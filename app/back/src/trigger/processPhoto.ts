import { task, logger, metadata } from "@trigger.dev/sdk";
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

export interface ExifData {
  latitude?: number;
  longitude?: number;
  dateTime?: string;
  camera?: string;
}

export interface ProcessPhotoResult {
  faces_count: number;
  boxes: BoundingBox[];
  blurred: boolean;
  exif: ExifData;
}

export const processPhotoTask = task({
  id: "process-photo",
  run: async (payload: ProcessPhotoPayload): Promise<ProcessPhotoResult> => {
    const { downloadUrl, uploadUrl, detSize = 1280 } = payload;

    // Stage 1: Extract EXIF data (fast, ~100ms)
    metadata.set("stage", "analyzing_location");
    logger.info("Stage: analyzing location (EXIF extraction)");

    const exifResult = await python.runScript("./scripts/extract_exif.py", [
      downloadUrl,
    ]);

    if (exifResult.stderr) {
      logger.info("EXIF extraction stderr", { stderr: exifResult.stderr });
    }

    const exifData: ExifData = JSON.parse(exifResult.stdout);
    logger.info("EXIF data extracted", { exif: exifData });

    // Stage 2: Detect faces, blur, and upload (slow, 5-20s)
    metadata.set("stage", "blurring_faces");
    logger.info("Stage: blurring faces");

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

    // Merge EXIF: prefer the dedicated extraction (ran before any processing)
    return {
      ...jsonResult,
      exif: {
        ...jsonResult.exif,
        ...exifData,
      },
    };
  },
});
