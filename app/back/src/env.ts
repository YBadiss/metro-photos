import dotenv from "dotenv";
import { existsSync } from "fs";
import { join } from "path";

// Load .env.local if it exists, otherwise .env
// Use process.cwd() to work both locally and in production
const envLocal = join(process.cwd(), ".env.local");
const envFile = join(process.cwd(), ".env");
dotenv.config({ path: existsSync(envLocal) ? envLocal : envFile });
