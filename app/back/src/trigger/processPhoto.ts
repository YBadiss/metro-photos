import { task, logger, metadata } from "@trigger.dev/sdk";
import { python } from "@trigger.dev/python";
import OpenAI from "openai";

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
  thumbnail?: string;
  validationConfidence: number;
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

    // Stage 2: Validate content with GPT-4o-mini vision (fast, ~1-2s)
    metadata.set("stage", "validating_content");
    logger.info("Stage: validating content with LLM");

    const CONFIDENCE_THRESHOLD = 70;

    async function callValidation(imageUrl: string): Promise<number> {
      const openai = new OpenAI();
      const chatResponse = await openai.chat.completions.create({
        model: "gpt-4o-mini",
        max_tokens: 50,
        temperature: 0.2,
        messages: [
          {
            role: "user",
            content: [
              {
                type: "image_url",
                image_url: { url: imageUrl, detail: "low" },
              },
              {
                type: "text",
                text: 'Is this a photo of a Paris metro entrance? Reply with JSON only: {"confidence": <0-100>}',
              },
            ],
          },
        ],
      });

      const text = chatResponse.choices[0]?.message?.content ?? "";
      const match = text.match(/\{[^}]*"confidence"\s*:\s*(\d+)[^}]*\}/);
      const confidence = match ? parseInt(match[1], 10) : 0;
      logger.info("Validation result", { raw: text, confidence });
      return confidence;
    }

    let validationConfidence = 0;
    try {
      validationConfidence = await callValidation(downloadUrl);

      // Retry once if below threshold, take the max
      if (validationConfidence < CONFIDENCE_THRESHOLD) {
        logger.info("First validation below threshold, retrying", { confidence: validationConfidence });
        const secondConfidence = await callValidation(downloadUrl);
        validationConfidence = Math.max(validationConfidence, secondConfidence);
      }
    } catch (err) {
      logger.error("Validation LLM call failed, defaulting to 0", { error: String(err) });
    }

    // Skip expensive processing if content validation failed
    if (validationConfidence < CONFIDENCE_THRESHOLD) {
      logger.info("Skipping face blurring for invalid photo", { confidence: validationConfidence });
      return {
        faces_count: 0,
        boxes: [],
        blurred: false,
        exif: exifData,
        validationConfidence,
      };
    }

    // Stage 3: Detect faces, blur, and upload (slow, 5-20s)
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
      validationConfidence,
    };
  },
});
