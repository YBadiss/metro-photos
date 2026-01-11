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
    
    # Clean up the mask
    kernel = np.ones((3, 3), np.uint8)
    cyan_mask = cv2.morphologyEx(cyan_mask, cv2.MORPH_CLOSE, kernel)
    cyan_mask = cv2.morphologyEx(cyan_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(cyan_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bounding_boxes = []
    
    for contour in contours:
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Filter out very small contours (noise)
        if w < 10 or h < 10:
            continue
        
        bounding_boxes.append({
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h)
        })
    
    # Merge overlapping/adjacent boxes (for rectangles detected as separate lines)
    merged_boxes = merge_nearby_boxes(bounding_boxes, threshold=20)
    
    # Filter boxes to keep only face-like shapes (roughly square, not too thin)
    filtered_boxes = []
    for box in merged_boxes:
        w, h = box["width"], box["height"]
        
        # Skip very thin boxes (aspect ratio check)
        aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
        if aspect_ratio > 3.0:
            continue
        
        # Skip very small boxes (minimum area for face-sized rectangles)
        if w * h < 2000:
            continue
            
        filtered_boxes.append(box)
    
    return filtered_boxes


def merge_nearby_boxes(boxes: list[dict], threshold: int = 20) -> list[dict]:
    """
    Merge bounding boxes that are close to each other.
    
    This handles cases where a rectangle's sides are detected as separate contours.
    """
    if not boxes:
        return []
    
    # Convert to a format easier to work with
    rects = [(b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"]) for b in boxes]
    
    merged = True
    while merged:
        merged = False
        new_rects = []
        used = set()
        
        for i, r1 in enumerate(rects):
            if i in used:
                continue
                
            x1_min, y1_min, x1_max, y1_max = r1
            
            for j, r2 in enumerate(rects):
                if j <= i or j in used:
                    continue
                
                x2_min, y2_min, x2_max, y2_max = r2
                
                # Check if boxes are close enough to merge
                # Either overlapping or within threshold distance
                if (x1_min - threshold <= x2_max and x2_min - threshold <= x1_max and
                    y1_min - threshold <= y2_max and y2_min - threshold <= y1_max):
                    # Merge the boxes
                    x1_min = min(x1_min, x2_min)
                    y1_min = min(y1_min, y2_min)
                    x1_max = max(x1_max, x2_max)
                    y1_max = max(y1_max, y2_max)
                    used.add(j)
                    merged = True
            
            new_rects.append((x1_min, y1_min, x1_max, y1_max))
            used.add(i)
        
        rects = new_rects
    
    # Convert back to dict format
    return [
        {"x": int(r[0]), "y": int(r[1]), "width": int(r[2] - r[0]), "height": int(r[3] - r[1])}
        for r in rects
    ]


def process_image(image_path: Path) -> int:
    """Process a single image and save JSON with same base name."""
    print(f"\nProcessing: {image_path.name}")
    
    boxes = extract_cyan_rectangles(str(image_path))
    
    print(f"  Found {len(boxes)} bounding boxes")
    for i, box in enumerate(boxes):
        print(f"    {i + 1}. x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}")
    
    # Output JSON with same base name
    output_path = image_path.parent / f"{image_path.stem}.json"
    
    result = {
        "source_image": str(image_path.stem),
        "boxes": boxes
    }
    
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
        help="Path to a specific target image (optional, processes all if not specified)"
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=TARGET_DIR,
        help=f"Directory containing target images (default: {TARGET_DIR})"
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
        images = [f for f in target_dir.iterdir() 
                  if f.is_file() and f.suffix.lower() in image_extensions]
        
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
