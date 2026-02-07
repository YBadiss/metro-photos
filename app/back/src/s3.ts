import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { v4 as uuidv4 } from "uuid";

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

const S3_ENDPOINT = requireEnv("S3_ENDPOINT");
const S3_REGION = requireEnv("S3_REGION");
const S3_ACCESS_KEY_ID = requireEnv("S3_ACCESS_KEY_ID");
const S3_SECRET_ACCESS_KEY = requireEnv("S3_SECRET_ACCESS_KEY");
const BUCKET_NAME = requireEnv("S3_BUCKET_NAME");

const s3Client = new S3Client({
  endpoint: S3_ENDPOINT,
  region: S3_REGION,
  credentials: {
    accessKeyId: S3_ACCESS_KEY_ID,
    secretAccessKey: S3_SECRET_ACCESS_KEY,
  },
  forcePathStyle: true,
});

const SIGNED_URL_EXPIRY = 60 * 15; // 15 minutes

export interface UploadUrlRequest {
  filename: string;
  contentType: string;
}

export interface UploadUrlResponse {
  uploadUrl: string;
  key: string;
  expiresIn: number;
}

export async function generateUploadUrl(request: UploadUrlRequest): Promise<UploadUrlResponse> {
  const extension = request.filename.split(".").pop() || "jpg";
  const key = `uploads/${uuidv4()}.${extension}`;

  const command = new PutObjectCommand({
    Bucket: BUCKET_NAME,
    Key: key,
    ContentType: request.contentType,
  });

  const uploadUrl = await getSignedUrl(s3Client, command, {
    expiresIn: SIGNED_URL_EXPIRY,
  });

  return {
    uploadUrl,
    key,
    expiresIn: SIGNED_URL_EXPIRY,
  };
}

export async function generateDownloadUrl(key: string): Promise<string> {
  const command = new GetObjectCommand({
    Bucket: BUCKET_NAME,
    Key: key,
  });

  return getSignedUrl(s3Client, command, {
    expiresIn: SIGNED_URL_EXPIRY,
  });
}
