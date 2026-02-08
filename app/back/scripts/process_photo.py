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
import base64
import json
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

import cv2
from PIL import Image
from PIL.ExifTags import Base as ExifBase

from detect_faces import detect_faces, download_image


def _dms_to_decimal(dms_tuple, ref: str) -> float:
    """Convert GPS degrees/minutes/seconds to decimal degrees."""
    degrees = float(dms_tuple[0])
    minutes = float(dms_tuple[1])
    seconds = float(dms_tuple[2])
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def extract_exif(image_path: str) -> dict:
    """Extract GPS, date, and camera info from image EXIF data."""
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if not exif:
            return {}

        result = {}

        # Camera make + model (top-level IFD)
        make = exif.get(ExifBase.Make, "")
        model = exif.get(ExifBase.Model, "")
        camera = " ".join(filter(None, [str(make).strip(), str(model).strip()]))
        if camera:
            result["camera"] = camera

        # DateTimeOriginal from EXIF sub-IFD (0x8769)
        exif_ifd = exif.get_ifd(0x8769)
        dt_original = exif_ifd.get(ExifBase.DateTimeOriginal)
        if dt_original:
            # Convert "2025:12:28 13:16:22" to ISO format
            try:
                from datetime import datetime

                dt = datetime.strptime(str(dt_original), "%Y:%m:%d %H:%M:%S")
                result["dateTime"] = dt.isoformat()
            except ValueError:
                result["dateTime"] = str(dt_original)

        # GPS from GPS sub-IFD (0x8825)
        gps_ifd = exif.get_ifd(0x8825)
        if gps_ifd:
            lat_ref = gps_ifd.get(1)  # GPSLatitudeRef
            lat_dms = gps_ifd.get(2)  # GPSLatitude
            lon_ref = gps_ifd.get(3)  # GPSLongitudeRef
            lon_dms = gps_ifd.get(4)  # GPSLongitude

            if lat_dms and lat_ref and lon_dms and lon_ref:
                result["latitude"] = round(_dms_to_decimal(lat_dms, lat_ref), 6)
                result["longitude"] = round(_dms_to_decimal(lon_dms, lon_ref), 6)

        return result
    except Exception as e:
        print(f"EXIF extraction failed: {e}", file=sys.stderr)
        return {}


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


def generate_thumbnail(image_path: str, max_width: int = 300, quality: int = 75) -> str:
    """Generate a small JPEG thumbnail and return it as a base64 string."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image for thumbnail: {image_path}")

    h, w = img.shape[:2]
    if w > max_width:
        scale = max_width / w
        new_w = max_width
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf).decode("ascii")


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

        # 2. Extract EXIF from original (before blurring strips it)
        exif_data = extract_exif(temp_input)
        print(f"EXIF data: {exif_data}", file=sys.stderr)

        # 3. Detect faces
        det_size = (args.det_size, args.det_size)
        boxes = detect_faces(temp_input, det_size=det_size)
        print(f"Detected {len(boxes)} face(s)", file=sys.stderr)

        # 4. Blur faces and save to temp file
        temp_output = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False).name
        if boxes:
            blur_faces(temp_input, boxes, temp_output)
        else:
            shutil.copy2(temp_input, temp_output)

        # 5. Upload blurred image
        print("Uploading blurred image...", file=sys.stderr)
        upload_to_presigned_url(temp_output, args.upload_url)

        # 5.5 Generate thumbnail from blurred image
        print("Generating thumbnail...", file=sys.stderr)
        thumbnail_b64 = generate_thumbnail(temp_output)
        print(f"Thumbnail size: {len(thumbnail_b64)} chars", file=sys.stderr)

        # 6. Output result as JSON to stdout
        result = {
            "faces_count": len(boxes),
            "boxes": boxes,
            "blurred": len(boxes) > 0,
            "exif": exif_data,
            "thumbnail": thumbnail_b64,
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
