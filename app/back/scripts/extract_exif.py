"""
Extract EXIF data (GPS, date, camera) from an image.

Usage:
    python extract_exif.py <download_url>

Outputs JSON to stdout:
    {
        "latitude": 48.858844,
        "longitude": 2.294351,
        "dateTime": "2025-12-28T13:16:22",
        "camera": "Apple iPhone 15 Pro"
    }
"""

import json
import sys
import tempfile
import urllib.request
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifBase


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


def download_image(url: str) -> str:
    """Download image from URL to a temporary file. Returns the temp file path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.close()
    urllib.request.urlretrieve(url, tmp.name)
    return tmp.name


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_exif.py <download_url>", file=sys.stderr)
        return 1

    download_url = sys.argv[1]
    temp_path = None

    try:
        temp_path = download_image(download_url)
        exif_data = extract_exif(temp_path)
        print(json.dumps(exif_data))
        return 0
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink()
            except OSError:
                pass


if __name__ == "__main__":
    exit(main())
