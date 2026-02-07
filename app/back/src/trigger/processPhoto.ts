import { task, logger } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";

interface ProcessPhotoPayload {
  downloadUrl: string;
  uploadUrl: string;
  detSize?: number;
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export interface ProcessPhotoResult {
  faces_count: number;
  boxes: BoundingBox[];
  blurred: boolean;
}

export const processPhotoTask = task({
  id: "process-photo",
  run: async (payload: ProcessPhotoPayload): Promise<ProcessPhotoResult> => {
    const { downloadUrl, uploadUrl, detSize = 1280 } = payload;

    logger.info("Starting photo processing (detect + blur)", { detSize });

    const result = await python.runScript("./scripts/process_photo.py", [
      downloadUrl,
      uploadUrl,
      "--det-size",
      detSize.toString(),
    ]);

    if (result.stderr) {
      logger.info("Python stderr output", { stderr: result.stderr });
    }

    const jsonResult: ProcessPhotoResult = JSON.parse(result.stdout);

    logger.info("Photo processing completed", {
      facesCount: jsonResult.faces_count,
      blurred: jsonResult.blurred,
    });

    return jsonResult;
  },
});
