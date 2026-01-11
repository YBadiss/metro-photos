import { defineConfig } from "@trigger.dev/sdk/v3";
import { pythonExtension } from "@trigger.dev/python/extension";

export default defineConfig({
  project: "proj_herluujeuxacgvcyiibo",
  runtime: "node",
  logLevel: "log",
  maxDuration: 300, // 5 minutes max for face detection
  retries: {
    enabledInDev: true,
    default: {
      maxAttempts: 3,
      minTimeoutInMs: 1000,
      maxTimeoutInMs: 10000,
      factor: 2,
    },
  },
  dirs: ["./src/trigger"],
  build: {
    extensions: [
      pythonExtension({
        scripts: ["./scripts/detect_faces.py"],
        requirementsFile: "./requirements.txt",
        // Use uv's venv Python in dev mode
        devPythonBinaryPath: "./scripts/.venv/bin/python",
      }),
    ],
  },
});
