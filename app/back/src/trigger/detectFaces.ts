import { task, logger } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

interface DetectFacesPayload {
  imageUrl: string;
  detSize?: number;
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

interface DetectFacesResult {
  source_image: string;
  detector: string;
  det_size: number;
  boxes: BoundingBox[];
}

export const detectFacesTask = task({
  id: "detect-faces",
  run: async (payload: DetectFacesPayload): Promise<DetectFacesResult> => {
    const { imageUrl, detSize = 1280 } = payload;

    logger.info("Starting face detection", { imageUrl, detSize });

    // Run the Python script with the image URL and detection size
    const result = await python.runScript("./scripts/detect_faces.py", [
      imageUrl,
      "--det-size",
      detSize.toString(),
    ]);

    if (result.stderr) {
      logger.warn("Python stderr output", { stderr: result.stderr });
    }

    // Parse the JSON output from the script
    const jsonResult: DetectFacesResult = JSON.parse(result.stdout);

    logger.info("Face detection completed", {
      imageUrl,
      facesDetected: jsonResult.boxes.length,
      result: jsonResult,
    });

    return jsonResult;
  },
});
