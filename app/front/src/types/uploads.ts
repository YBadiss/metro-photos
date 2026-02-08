export interface ExifData {
  latitude?: number;
  longitude?: number;
  dateTime?: string;
  camera?: string;
}

export interface MatchedEntrance {
  entrance: { id: string; name: string; short_name: number | null };
  station: { id: string; name: string; town: string };
  lines: Array<{ id: string; name: string; icon_url: string | null; color?: string }>;
  distanceMeters: number;
}

export interface ProcessingResult {
  blurredUrl: string;
  blurredKey: string;
  facesCount: number;
  exif?: ExifData;
  matchedEntrance?: MatchedEntrance | null;
}

export type ProcessingStage = "queued" | "analyzing_location" | "blurring_faces" | "validating_content" | "finalizing";

export interface FileUpload {
  id: string;
  file: File;
  status: "pending" | "uploading" | "processing" | "processed" | "validated" | "error";
  processingStage?: ProcessingStage;
  progress: number;
  error?: string;
  key?: string;
  runId?: string;
  result?: ProcessingResult;
  photoId?: number;
}
