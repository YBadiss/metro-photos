"""
Extract cyan bounding boxes from target images.

This script detects cyan rectangles drawn on images and exports their
bounding box coordinates to JSON for evaluation of face detection algorithms.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


# Default directories
SCRIPT_DIR = Path(__file__).parent
TARGET_DIR = SCRIPT_DIR / "target"


def extract_cyan_rectangles(image_path: str) -> list[dict]:
    """
    Extract cyan rectangle bounding boxes from an image.

    Args:
        image_path: Path to the image with cyan rectangles marking targets

    Returns:
        List of bounding boxes as dicts with x, y, width, height
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Cyan detection - hue around 85-95 in OpenCV's 0-180 scale
    # Pure cyan (#00FFFF) has hue ~90
    lower_cyan = np.array([80, 100, 100])
    upper_cyan = np.array([100, 255, 255])
    cyan_mask = cv2.inRange(hsv, lower_cyan, upper_cyan)

    # Clean up noise
    kernel_small = np.ones((3, 3), np.uint8)
    cyan_mask = cv2.morphologyEx(cyan_mask, cv2.MORPH_OPEN, kernel_small)

    # Fill in the rectangle outlines using flood fill approach:
    # 1. Find contours of the cyan pixels
    # 2. For each contour, if it looks like a rectangle outline, fill it
    contours, hierarchy = cv2.findContours(
        cyan_mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
    )

    # Create a filled mask
    filled_mask = cyan_mask.copy()

    for i, contour in enumerate(contours):
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)

        # Skip tiny contours
        if w < 20 or h < 20:
            continue

        # Check if this looks like a rectangle outline (hollow)
        # by checking if the contour area is much smaller than the bounding rect area
        contour_area = cv2.contourArea(contour)
        rect_area = w * h

        # If contour area is small relative to bounding rect, it's likely a hollow rectangle
        # Fill it in
        if contour_area < rect_area * 0.5:
            cv2.rectangle(filled_mask, (x, y), (x + w, y + h), 255, -1)

    # Find contours of the filled shapes
    final_contours, _ = cv2.findContours(
        filled_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    bounding_boxes = []
    for contour in final_contours:
        x, y, w, h = cv2.boundingRect(contour)

        # Filter out small contours (noise)
        if w < 30 or h < 30:
            continue

        # Skip very thin boxes (aspect ratio check)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float("inf")
        if aspect_ratio > 3.0:
            continue

        # Skip very small boxes
        if w * h < 2000:
            continue

        bounding_boxes.append(
            {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
        )

    return bounding_boxes


def process_image(image_path: Path) -> int:
    """Process a single image and save JSON with same base name."""
    print(f"\nProcessing: {image_path.name}")

    boxes = extract_cyan_rectangles(str(image_path))

    print(f"  Found {len(boxes)} bounding boxes")
    for i, box in enumerate(boxes):
        print(
            f"    {i + 1}. x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}"
        )

    # Output JSON with same base name
    output_path = image_path.parent / f"{image_path.stem}.json"

    result = {"source_image": str(image_path.stem), "boxes": boxes}

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  Saved to: {output_path.name}")
    return len(boxes)


def main():
    parser = argparse.ArgumentParser(
        description="Extract cyan bounding boxes from target images"
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to a specific target image (optional, processes all if not specified)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=TARGET_DIR,
        help=f"Directory containing target images (default: {TARGET_DIR})",
    )

    args = parser.parse_args()

    if args.image:
        # Process single image
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: Image not found: {image_path}")
            return 1
        process_image(image_path)
    else:
        # Process all images in target directory
        target_dir = args.target_dir
        if not target_dir.exists():
            print(f"Error: Target directory not found: {target_dir}")
            return 1

        image_extensions = {".jpg", ".jpeg", ".png"}
        images = [
            f
            for f in target_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not images:
            print(f"No images found in {target_dir}")
            return 1

        print(f"Processing {len(images)} images from {target_dir}")

        total_boxes = 0
        for image_path in sorted(images):
            total_boxes += process_image(image_path)

        print(f"\n{'='*50}")
        print(f"Total: {total_boxes} ground truth boxes from {len(images)} images")

    return 0


if __name__ == "__main__":
    exit(main())
