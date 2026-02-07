import { defineConfig } from "@trigger.dev/sdk";
import { pythonExtension } from "@trigger.dev/python/extension";
import type { BuildExtension } from "@trigger.dev/core/v3/build";

function systemPackages(packages: string[]): BuildExtension {
  return {
    name: "systemPackages",
    onBuildComplete(context) {
      if (context.target === "dev") return;
      context.addLayer({
        id: "system-packages",
        image: {
          instructions: [
            `RUN apt-get update && apt-get install -y --no-install-recommends ${packages.join(" ")} && apt-get clean && rm -rf /var/lib/apt/lists/*`,
          ],
        },
      });
    },
  };
}

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
      systemPackages(["build-essential", "cmake", "python3-dev"]),
      pythonExtension({
        scripts: ["./scripts/detect_faces.py", "./scripts/process_photo.py"],
        requirementsFile: "./requirements.txt",
        // Use uv's venv Python in dev mode
        devPythonBinaryPath: "./scripts/.venv/bin/python",
      }),
    ],
  },
});
