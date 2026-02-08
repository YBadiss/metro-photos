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
import type { processPhotoTask, ProcessPhotoResult } from "./trigger/processPhoto";
import { db } from "./db";
import {
  zones as zonesTable,
  accesses as accessesTable,
  lines as linesTable,
  zoneLines,
  photos as photosTable,
} from "./db/schema";
import { eq } from "drizzle-orm";

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
  res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
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

// Process a photo: detect faces, blur them, upload result
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

    // Poll for completion
    const run = await runs.poll(handle, { pollIntervalMs: 1000 });

    if (run.status !== "COMPLETED") {
      console.error("Photo processing task failed:", run.error);
      res.status(500).json({ error: "Photo processing failed", details: run.error });
      return;
    }

    // Generate a download URL for the blurred image
    const blurredUrl = await generateDownloadUrl(processedKey);

    const output = run.output as ProcessPhotoResult;

    console.log("Photo processing result:", JSON.stringify(output, null, 2));

    // Delete the original upload from S3 (only keep the blurred version)
    await deleteObject(imageKey);

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

    // Persist photo metadata if matched to an entrance
    if (matchedEntrance) {
      await db.insert(photosTable).values({
        s3Key: processedKey,
        accessId: matchedEntrance.entrance.id,
        latitude: output.exif?.latitude ?? null,
        longitude: output.exif?.longitude ?? null,
        takenAt: output.exif?.dateTime ? new Date(output.exif.dateTime) : null,
        camera: output.exif?.camera ?? null,
      });
    }

    res.json({
      blurredKey: processedKey,
      blurredUrl,
      facesCount: output.faces_count,
      blurred: output.blurred,
      exif: output.exif,
      matchedEntrance,
    });
  } catch (error) {
    console.error("Error processing photo:", error);
    res.status(500).json({ error: "Failed to process photo" });
  }
});

// List photos for a given entrance
app.get("/accesses/:id/photos", async (req, res) => {
  try {
    const accessId = req.params.id;
    const rows = await db.select().from(photosTable).where(eq(photosTable.accessId, accessId));

    const results = await Promise.all(
      rows.map(async (row) => ({
        id: row.id,
        s3Key: row.s3Key,
        url: await generateDownloadUrl(row.s3Key),
        latitude: row.latitude,
        longitude: row.longitude,
        takenAt: row.takenAt,
        camera: row.camera,
        createdAt: row.createdAt,
      })),
    );

    res.json(results);
  } catch (error) {
    console.error("Error fetching photos:", error);
    res.status(500).json({ error: "Failed to fetch photos" });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
