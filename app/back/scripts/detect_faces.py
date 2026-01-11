"""
Face detection using RetinaFace (via InsightFace).

Detects faces in images and outputs bounding boxes as JSON.
Supports both local file paths and URLs.
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

# Suppress onnxruntime and insightface logging to stdout/stderr
os.environ["ONNXRUNTIME_LOGGING_LEVEL"] = "ERROR"

import cv2

# Suppress insightface stdout output during import
with redirect_stdout(StringIO()):
    from insightface.app import FaceAnalysis


# Global face analyzer (lazy initialization)
_face_analyzer = None
_current_det_size = None


def is_url(path: str) -> bool:
    """Check if the given path is a URL."""
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")


def download_image(url: str) -> str:
    """Download an image from a URL to a temporary file and return the path."""
    # Extract extension from URL or default to .jpg
    parsed = urlparse(url)
    path_part = parsed.path
    ext = Path(path_part).suffix if Path(path_part).suffix else ".jpg"

    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_path = temp_file.name
    temp_file.close()

    # Download the image
    urllib.request.urlretrieve(url, temp_path)
    return temp_path


def get_face_analyzer(det_size: tuple[int, int] = (640, 640)):
    """Get or initialize the face analyzer."""
    global _face_analyzer, _current_det_size
    if _face_analyzer is None or _current_det_size != det_size:
        # Suppress stdout during model initialization
        with redirect_stdout(StringIO()):
            # Initialize with RetinaFace detection model
            _face_analyzer = FaceAnalysis(
                name="buffalo_sc",  # Smaller model, good for detection
                allowed_modules=["detection"],  # Only load detection, not recognition
                providers=["CPUExecutionProvider"],
            )
            _face_analyzer.prepare(ctx_id=-1, det_size=det_size)  # -1 for CPU
        _current_det_size = det_size
    return _face_analyzer


def detect_faces(image_path: str, det_size: tuple[int, int] = (640, 640)) -> list[dict]:
    """
    Detect faces in an image using RetinaFace (via InsightFace).

    Args:
        image_path: Path to the image
        det_size: Detection input size (larger = better for small faces but slower)

    Returns:
        List of bounding boxes as dicts with x, y, width, height, confidence
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    app = get_face_analyzer(det_size=det_size)
    faces = app.get(img)

    bounding_boxes = []
    for face in faces:
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        confidence = float(face.det_score)

        bounding_boxes.append(
            {
                "x": int(x1),
                "y": int(y1),
                "width": int(x2 - x1),
                "height": int(y2 - y1),
                "confidence": confidence,
            }
        )

    return bounding_boxes


def main():
    parser = argparse.ArgumentParser(
        description="Detect faces in an image and output bounding boxes as JSON"
    )
    parser.add_argument(
        "image", help="Path to the image to process (can be a local path or URL)"
    )
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    parser.add_argument(
        "--det-size",
        type=int,
        default=1280,
        help="Detection input size (default: 1280). Larger = better for small faces but slower",
    )

    args = parser.parse_args()

    image_input = args.image
    temp_file = None

    # Handle URL input
    if is_url(image_input):
        print(f"Downloading image from URL: {image_input}", file=sys.stderr)
        temp_file = download_image(image_input)
        image_path = Path(temp_file)
        source_name = Path(urlparse(image_input).path).name or "downloaded_image"
    else:
        image_path = Path(image_input)
        source_name = image_path.name
        if not image_path.exists():
            print(f"Error: Image not found: {image_path}", file=sys.stderr)
            return 1

    try:
        det_size = (args.det_size, args.det_size)
        boxes = detect_faces(str(image_path), det_size=det_size)

        result = {
            "source_image": source_name,
            "detector": "retinaface",
            "det_size": det_size[0],
            "boxes": boxes,
        }

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))

        return 0
    finally:
        # Clean up temporary file if we downloaded one
        if temp_file:
            try:
                Path(temp_file).unlink()
            except OSError:
                pass


if __name__ == "__main__":
    exit(main())
