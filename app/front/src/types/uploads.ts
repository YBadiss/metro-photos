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

export interface FileUpload {
  id: string;
  file: File;
  status: "pending" | "uploading" | "processing" | "processed" | "validated" | "error";
  progress: number;
  error?: string;
  key?: string;
  result?: ProcessingResult;
  photoId?: number;
}
