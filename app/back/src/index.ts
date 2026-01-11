import "./env"; // Must be first to load env vars before other imports
import cors from "cors";
import express from "express";
import { readFileSync } from "fs";
import { join } from "path";
import { generateUploadUrl, generateDownloadUrl } from "./s3";
import { tasks, runs } from "@trigger.dev/sdk/v3";
import type { detectFacesTask } from "./trigger/detectFaces";

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS for frontend
app.use(cors());
app.use(express.json());

// Load zones_metro.json from data folder
// Use process.cwd() because:
// - Local: tsx runs from app/back/, data is at ./data/
// - Prod: pm2 runs from deploy dir, data is at ./data/
const dataPath = join(process.cwd(), "data/zones_metro.json");
const zonesMetro = JSON.parse(readFileSync(dataPath, "utf-8"));

app.get("/zones_metro", (_req, res) => {
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
    const handle = await tasks.trigger<typeof detectFacesTask>(
      "detect-faces",
      { imageUrl, detSize }
    );

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

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
