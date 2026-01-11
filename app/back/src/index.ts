import "./env"; // Must be first to load env vars before other imports
import cors from "cors";
import express from "express";
import { readFileSync } from "fs";
import { join } from "path";
import { generateUploadUrl } from "./s3";

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS for frontend
app.use(cors());
app.use(express.json());

// Load zones_metro.json from data folder
const dataPath = join(__dirname, "../data/zones_metro.json");
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

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
