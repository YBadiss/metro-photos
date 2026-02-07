"""
Process a photo: download from S3, detect faces, blur them, upload result.

Usage:
    python process_photo.py <download_url> <upload_url> [--det-size 1280]

Outputs JSON to stdout:
    {
        "faces_count": 3,
        "boxes": [{ "x": ..., "y": ..., "width": ..., "height": ..., "confidence": ... }],
        "blurred": true
    }
"""

import argparse
import json
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

import cv2

from detect_faces import detect_faces, download_image


def blur_faces(image_path: str, boxes: list[dict], output_path: str) -> None:
    """Apply Gaussian blur to detected face regions and save result."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    for box in boxes:
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        # Clamp to image boundaries
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(img.shape[1], x + w)
        y2 = min(img.shape[0], y + h)

        if x2 > x1 and y2 > y1:
            face_region = img[y1:y2, x1:x2]
            # Kernel size proportional to face size, must be odd
            ksize = max(99, (min(w, h) // 3) | 1)
            blurred = cv2.GaussianBlur(face_region, (ksize, ksize), 30)
            img[y1:y2, x1:x2] = blurred

    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 90])


def upload_to_presigned_url(file_path: str, upload_url: str) -> None:
    """Upload a file to an S3 presigned PUT URL."""
    with open(file_path, "rb") as f:
        data = f.read()

    req = urllib.request.Request(
        upload_url,
        data=data,
        method="PUT",
        headers={"Content-Type": "image/jpeg"},
    )
    urllib.request.urlopen(req)


def main():
    parser = argparse.ArgumentParser(
        description="Detect faces, blur them, upload result"
    )
    parser.add_argument(
        "download_url", help="Presigned download URL for the source image"
    )
    parser.add_argument(
        "upload_url", help="Presigned PUT URL for the blurred output"
    )
    parser.add_argument("--det-size", type=int, default=1280)
    args = parser.parse_args()

    temp_input = None
    temp_output = None

    try:
        # 1. Download the original image
        print("Downloading source image...", file=sys.stderr)
        temp_input = download_image(args.download_url)

        # 2. Detect faces
        det_size = (args.det_size, args.det_size)
        boxes = detect_faces(temp_input, det_size=det_size)
        print(f"Detected {len(boxes)} face(s)", file=sys.stderr)

        # 3. Blur faces and save to temp file
        temp_output = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False).name
        if boxes:
            blur_faces(temp_input, boxes, temp_output)
        else:
            shutil.copy2(temp_input, temp_output)

        # 4. Upload blurred image
        print("Uploading blurred image...", file=sys.stderr)
        upload_to_presigned_url(temp_output, args.upload_url)

        # 5. Output result as JSON to stdout
        result = {
            "faces_count": len(boxes),
            "boxes": boxes,
            "blurred": len(boxes) > 0,
        }
        print(json.dumps(result))
        return 0

    finally:
        for path in [temp_input, temp_output]:
            if path:
                try:
                    Path(path).unlink()
                except OSError:
                    pass


if __name__ == "__main__":
    exit(main())
