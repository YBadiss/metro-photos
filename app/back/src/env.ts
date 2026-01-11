import dotenv from "dotenv";
import { existsSync } from "fs";
import { join } from "path";

// Load .env.local if it exists, otherwise .env
const envLocal = join(__dirname, "../.env.local");
const envFile = join(__dirname, "../.env");
dotenv.config({ path: existsSync(envLocal) ? envLocal : envFile });
