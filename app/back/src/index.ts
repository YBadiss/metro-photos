import "./env"; // Must be first to load env vars before other imports
import express from "express";
import {
  generateUploadUrl,
  generateUploadUrlForKey,
  generateDownloadUrl,
  deleteObject,
} from "./s3";
import { tasks, runs } from "@trigger.dev/sdk";
import type { detectFacesTask } from "./trigger/detectFaces";
import type { processPhotoTask, ProcessPhotoResult, ExifData } from "./trigger/processPhoto";
import { db } from "./db";
import {
  zones as zonesTable,
  accesses as accessesTable,
  lines as linesTable,
  zoneLines,
  photos as photosTable,
} from "./db/schema";
import { eq, desc, inArray, and } from "drizzle-orm";

// Metro data types (matching front/src/types/metro.ts)
interface GeoPoint {
  lat: number;
  lon: number;
}
interface Access {
  id: string;
  name: string;
  short_name: number | null;
  geo_point: GeoPoint;
}
interface Line {
  id: string;
  name: string;
  icon_url: string | null;
  color?: string;
}
interface Zone {
  id: string;
  name: string;
  town: string;
  accesses: Access[];
  lines: Line[];
}

interface MatchedEntrance {
  entrance: { id: string; name: string; short_name: number | null };
  station: { id: string; name: string; town: string };
  lines: Line[];
  distanceMeters: number;
}

function haversineMeters(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

const MAX_MATCH_DISTANCE_METERS = 500;

function findNearestEntrance(lat: number, lon: number, zones: Zone[]): MatchedEntrance | null {
  let best: MatchedEntrance | null = null;
  let bestDistance = Infinity;

  for (const zone of zones) {
    for (const access of zone.accesses) {
      const d = haversineMeters(lat, lon, access.geo_point.lat, access.geo_point.lon);
      if (d < bestDistance) {
        bestDistance = d;
        best = {
          entrance: { id: access.id, name: access.name, short_name: access.short_name },
          station: { id: zone.id, name: zone.name, town: zone.town },
          lines: zone.lines,
          distanceMeters: Math.round(d),
        };
      }
    }
  }

  if (best && best.distanceMeters > MAX_MATCH_DISTANCE_METERS) {
    return null;
  }

  return best;
}

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS for frontend
app.use((_req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  next();
});
app.use(express.json());

async function loadZonesFromDb(): Promise<Zone[]> {
  const allZones = await db.select().from(zonesTable);
  const allAccesses = await db.select().from(accessesTable);
  const allZoneLines = await db
    .select({
      zoneId: zoneLines.zoneId,
      id: linesTable.id,
      name: linesTable.name,
      color: linesTable.color,
      iconUrl: linesTable.iconUrl,
      iconFilename: linesTable.iconFilename,
    })
    .from(zoneLines)
    .innerJoin(linesTable, eq(zoneLines.lineId, linesTable.id));

  const accessesByZone = new Map<string, Access[]>();
  for (const a of allAccesses) {
    const list = accessesByZone.get(a.zoneId) ?? [];
    list.push({
      id: a.id,
      name: a.name,
      short_name: a.shortName,
      geo_point: { lon: a.lon, lat: a.lat },
    });
    accessesByZone.set(a.zoneId, list);
  }

  const linesByZone = new Map<string, Line[]>();
  for (const zl of allZoneLines) {
    const list = linesByZone.get(zl.zoneId) ?? [];
    list.push({
      id: zl.id,
      name: zl.name,
      color: zl.color,
      icon_url: zl.iconUrl,
    });
    linesByZone.set(zl.zoneId, list);
  }

  return allZones.map((z) => ({
    id: z.id,
    name: z.name,
    town: z.town,
    accesses: accessesByZone.get(z.id) ?? [],
    lines: linesByZone.get(z.id) ?? [],
  }));
}

// Cache zones in memory after first load
let zonesMetro: Zone[] | null = null;

// Track pending processing runs for async status polling
interface PendingRun {
  imageKey: string;
  processedKey: string;
}

interface FinalizedResult {
  photoId: number;
  blurredUrl: string;
  blurredKey: string;
  facesCount: number;
  blurred: boolean;
  exif: ExifData | null;
  matchedEntrance: MatchedEntrance | null;
  status: string;
}

const pendingRuns = new Map<string, PendingRun>();
const finalizedResults = new Map<string, FinalizedResult>();

app.get("/zones_metro", async (_req, res) => {
  if (!zonesMetro) {
    zonesMetro = await loadZonesFromDb();
  }
  res.json(zonesMetro);
});

// Request a presigned URL for uploading a photo
app.post("/upload-url", async (req, res) => {
  try {
    const { filename, contentType } = req.body;

    if (!filename || !contentType) {
      res.status(400).json({ error: "filename and contentType are required" });
      return;
    }

    // Validate content type is an image
    if (!contentType.startsWith("image/")) {
      res.status(400).json({ error: "Only image uploads are allowed" });
      return;
    }

    const result = await generateUploadUrl({ filename, contentType });
    res.json(result);
  } catch (error) {
    console.error("Error generating upload URL:", error);
    res.status(500).json({ error: "Failed to generate upload URL" });
  }
});

// Trigger face detection on an image stored in S3
app.post("/detect_faces", async (req, res) => {
  try {
    const { imageKey, detSize } = req.body;

    if (!imageKey) {
      res.status(400).json({ error: "imageKey is required" });
      return;
    }

    console.log("Triggering face detection for S3 key:", imageKey);

    // Generate a presigned URL for the image
    const imageUrl = await generateDownloadUrl(imageKey);

    // Trigger the task
    const handle = await tasks.trigger<typeof detectFacesTask>("detect-faces", {
      imageUrl,
      detSize,
    });

    console.log("Task triggered with ID:", handle.id);

    // Poll for the task to complete
    const run = await runs.poll(handle, { pollIntervalMs: 1000 });

    if (run.status !== "COMPLETED") {
      console.error("Face detection task failed:", run.error);
      res.status(500).json({ error: "Face detection failed", details: run.error });
      return;
    }

    console.log("Face detection result:", JSON.stringify(run.output, null, 2));

    res.json(run.output);
  } catch (error) {
    console.error("Error triggering face detection:", error);
    res.status(500).json({ error: "Failed to trigger face detection" });
  }
});

// Trigger photo processing (async - returns runId immediately)
app.post("/process-photo", async (req, res) => {
  try {
    const { imageKey, detSize } = req.body;

    if (!imageKey) {
      res.status(400).json({ error: "imageKey is required" });
      return;
    }

    console.log("Processing photo for S3 key:", imageKey);

    // Generate download URL for the original image
    const downloadUrl = await generateDownloadUrl(imageKey);

    // Generate upload URL for the blurred result under processed/ prefix
    const processedKey = imageKey.replace("uploads/", "processed/");
    const { uploadUrl } = await generateUploadUrlForKey(processedKey, "image/jpeg");

    // Trigger the combined detect + blur task
    const handle = await tasks.trigger<typeof processPhotoTask>("process-photo", {
      downloadUrl,
      uploadUrl,
      detSize,
    });

    console.log("Process-photo task triggered with ID:", handle.id);

    // Store context for finalization later
    pendingRuns.set(handle.id, { imageKey, processedKey });

    res.json({ runId: handle.id });
  } catch (error) {
    console.error("Error triggering photo processing:", error);
    res.status(500).json({ error: "Failed to trigger photo processing" });
  }
});

// Poll processing status for a given run
app.get("/process-photo/:runId/status", async (req, res) => {
  try {
    const { runId } = req.params;

    // Check if already finalized
    const cached = finalizedResults.get(runId);
    if (cached) {
      res.json({ stage: "finalized", result: cached });
      return;
    }

    // Check we have context for this run
    const pending = pendingRuns.get(runId);
    if (!pending) {
      res.status(404).json({ error: "Run not found" });
      return;
    }

    // Retrieve run status from trigger.dev
    const run = await runs.retrieve(runId);

    if (run.status === "COMPLETED") {
      // Perform finalization
      const output = run.output as ProcessPhotoResult;

      console.log("Photo processing result", output.validationConfidence);

      // Generate a download URL for the blurred image
      const blurredUrl = await generateDownloadUrl(pending.processedKey);

      // Delete the original upload from S3 (only keep the blurred version)
      await deleteObject(pending.imageKey);

      // Match GPS coordinates to nearest metro entrance
      let matchedEntrance: MatchedEntrance | null = null;
      if (output.exif?.latitude != null && output.exif?.longitude != null) {
        if (!zonesMetro) {
          zonesMetro = await loadZonesFromDb();
        }
        matchedEntrance = findNearestEntrance(
          output.exif.latitude,
          output.exif.longitude,
          zonesMetro,
        );
      }

      // Determine status: invalid if LLM confidence too low, no GPS, or no nearby entrance
      const hasGps = output.exif?.latitude != null && output.exif?.longitude != null;
      const photoStatus =
        output.validationConfidence >= 70 && hasGps && matchedEntrance
          ? "pending"
          : "invalid";

      // Always persist photo metadata
      const [insertedPhoto] = await db
        .insert(photosTable)
        .values({
          s3Key: pending.processedKey,
          accessId: matchedEntrance?.entrance.id ?? null,
          latitude: output.exif?.latitude ?? null,
          longitude: output.exif?.longitude ?? null,
          takenAt: output.exif?.dateTime ? new Date(output.exif.dateTime) : null,
          camera: output.exif?.camera ?? null,
          status: photoStatus,
          thumbnail: output.thumbnail ?? null,
        })
        .returning();

      const result: FinalizedResult = {
        photoId: insertedPhoto.id,
        blurredKey: pending.processedKey,
        blurredUrl,
        facesCount: output.faces_count,
        blurred: output.blurred,
        exif: output.exif ?? null,
        matchedEntrance,
        status: photoStatus,
      };

      // Cache result and clean up pending context
      finalizedResults.set(runId, result);
      pendingRuns.delete(runId);

      res.json({ stage: "finalized", result });
      return;
    }

    if (run.status === "FAILED" || run.status === "CANCELED" || run.status === "CRASHED") {
      pendingRuns.delete(runId);
      res.json({ stage: "error", error: "Processing failed" });
      return;
    }

    // Still running — read metadata for current stage
    const runMetadata = (run.metadata ?? {}) as Record<string, unknown>;
    const stage = (runMetadata.stage as string) ?? "queued";

    res.json({ stage });
  } catch (error) {
    console.error("Error checking process status:", error);
    res.status(500).json({ error: "Failed to check processing status" });
  }
});

// List latest validated photos
app.get("/photos/latest", async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit as string) || 10, 50);
    const rows = await db
      .select()
      .from(photosTable)
      .where(eq(photosTable.status, "validated"))
      .orderBy(desc(photosTable.createdAt))
      .limit(limit);

    const results = rows.map((row) => ({
      id: row.id,
      thumbnail: row.thumbnail,
      accessId: row.accessId,
      latitude: row.latitude,
      longitude: row.longitude,
      takenAt: row.takenAt,
      camera: row.camera,
      createdAt: row.createdAt,
    }));

    res.json(results);
  } catch (error) {
    console.error("Error fetching latest photos:", error);
    res.status(500).json({ error: "Failed to fetch latest photos" });
  }
});

// List all photos for a given station (zone)
app.get("/zones/:id/photos", async (req, res) => {
  try {
    const zoneId = req.params.id;
    const zoneAccesses = await db
      .select({ id: accessesTable.id })
      .from(accessesTable)
      .where(eq(accessesTable.zoneId, zoneId));

    const accessIds = zoneAccesses.map((a) => a.id);
    if (accessIds.length === 0) {
      res.json([]);
      return;
    }

    const rows = await db
      .select()
      .from(photosTable)
      .where(and(inArray(photosTable.accessId, accessIds), eq(photosTable.status, "validated")));

    const results = rows.map((row) => ({
      id: row.id,
      thumbnail: row.thumbnail,
      accessId: row.accessId,
      latitude: row.latitude,
      longitude: row.longitude,
      takenAt: row.takenAt,
      camera: row.camera,
      createdAt: row.createdAt,
    }));

    res.json(results);
  } catch (error) {
    console.error("Error fetching zone photos:", error);
    res.status(500).json({ error: "Failed to fetch photos" });
  }
});

// List photos for a given entrance
app.get("/accesses/:id/photos", async (req, res) => {
  try {
    const accessId = req.params.id;
    const rows = await db
      .select()
      .from(photosTable)
      .where(and(eq(photosTable.accessId, accessId), eq(photosTable.status, "validated")));

    const results = rows.map((row) => ({
      id: row.id,
      thumbnail: row.thumbnail,
      latitude: row.latitude,
      longitude: row.longitude,
      takenAt: row.takenAt,
      camera: row.camera,
      createdAt: row.createdAt,
    }));

    res.json(results);
  } catch (error) {
    console.error("Error fetching photos:", error);
    res.status(500).json({ error: "Failed to fetch photos" });
  }
});

// Get a presigned URL for a single photo (for full-res viewing)
app.get("/photos/:id/url", async (req, res) => {
  try {
    const photoId = parseInt(req.params.id, 10);
    if (isNaN(photoId)) {
      res.status(400).json({ error: "Invalid photo ID" });
      return;
    }

    const [photo] = await db.select().from(photosTable).where(eq(photosTable.id, photoId));
    if (!photo) {
      res.status(404).json({ error: "Photo not found" });
      return;
    }

    const url = await generateDownloadUrl(photo.s3Key);
    res.json({ url });
  } catch (error) {
    console.error("Error generating photo URL:", error);
    res.status(500).json({ error: "Failed to generate photo URL" });
  }
});

// Update a photo (validate, reassign entrance)
app.patch("/photos/:id", async (req, res) => {
  try {
    const photoId = parseInt(req.params.id, 10);
    if (isNaN(photoId)) {
      res.status(400).json({ error: "Invalid photo ID" });
      return;
    }

    const { status, accessId } = req.body;

    const updates: Record<string, unknown> = {};

    if (status !== undefined) {
      if (status !== "validated") {
        res.status(400).json({ error: "Status can only be set to 'validated'" });
        return;
      }
      updates.status = status;
    }

    if (accessId !== undefined) {
      // Verify access exists
      const [access] = await db.select().from(accessesTable).where(eq(accessesTable.id, accessId));
      if (!access) {
        res.status(404).json({ error: "Access not found" });
        return;
      }
      updates.accessId = accessId;
    }

    if (Object.keys(updates).length === 0) {
      res.status(400).json({ error: "No valid fields to update" });
      return;
    }

    const [updated] = await db
      .update(photosTable)
      .set(updates)
      .where(eq(photosTable.id, photoId))
      .returning();

    if (!updated) {
      res.status(404).json({ error: "Photo not found" });
      return;
    }

    // Generate presigned URL for the response
    const url = await generateDownloadUrl(updated.s3Key);

    res.json({ ...updated, url });
  } catch (error) {
    console.error("Error updating photo:", error);
    res.status(500).json({ error: "Failed to update photo" });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
