import cors from "cors";
import express from "express";
import { readFileSync } from "fs";
import { join } from "path";

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS for frontend
app.use(cors());

// Load zones_metro.json from data folder
const dataPath = join(__dirname, "data/zones_metro.json");
const zonesMetro = JSON.parse(readFileSync(dataPath, "utf-8"));

app.get("/zones_metro", (_req, res) => {
  res.json(zonesMetro);
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
