"""
Run face detection tests and generate visualizations.

This script orchestrates the detection testing workflow:
1. Runs detect_faces.py on all source images
2. Saves detection results as JSON to result/
3. Creates visualizations showing both detected (green) and ground truth (cyan) boxes
"""

import argparse
import json
import sys
from pathlib import Path

import cv2

# Add scripts directory to path for importing detect_faces
SCRIPT_DIR = Path(__file__).parent
SCRIPTS_DIR = SCRIPT_DIR.parent.parent  # scripts/
sys.path.insert(0, str(SCRIPTS_DIR))

from detect_faces import detect_faces  # noqa: E402

# Default directories
SOURCE_DIR = SCRIPT_DIR / "source"
TARGET_DIR = SCRIPT_DIR / "target"
RESULT_DIR = SCRIPT_DIR / "result"


def create_visualization(
    source_image_path: Path,
    detected_boxes: list[dict],
    ground_truth_boxes: list[dict],
    output_path: Path,
):
    """Create visualization with both detected and ground truth boxes."""
    img = cv2.imread(str(source_image_path))
    if img is None:
        print(f"  Warning: Could not load image for visualization: {source_image_path}")
        return

    # Draw ground truth boxes first (cyan, underneath)
    for gt_box in ground_truth_boxes:
        x, y, w, h = gt_box["x"], gt_box["y"], gt_box["width"], gt_box["height"]
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 0), 3)  # Cyan (BGR)

    # Draw detection boxes on top (green)
    for box in detected_boxes:
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]
        conf = box.get("confidence", 0)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)  # Green
        label = f"{conf:.2f}"
        cv2.putText(
            img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
        )

    cv2.imwrite(str(output_path), img)


def process_image(
    source_path: Path,
    target_dir: Path,
    result_dir: Path,
    det_size: tuple[int, int],
    visualize: bool,
) -> tuple[int, int]:
    """
    Process a single image.

    Returns:
        Tuple of (detected_count, ground_truth_count)
    """
    print(f"\nProcessing: {source_path.name}")

    # Run detection
    boxes = detect_faces(str(source_path), det_size=det_size)
    print(f"  Detected: {len(boxes)} faces")

    # Save detection JSON
    result = {
        "source_image": source_path.stem,
        "detector": "retinaface",
        "det_size": det_size[0],
        "boxes": boxes,
    }

    json_path = result_dir / f"{source_path.stem}.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)

    # Load ground truth
    gt_boxes = []
    gt_json_path = target_dir / f"{source_path.stem}.json"
    if gt_json_path.exists():
        with open(gt_json_path) as f:
            gt_data = json.load(f)
            gt_boxes = gt_data.get("boxes", [])
        print(f"  Ground truth: {len(gt_boxes)} faces")
    else:
        print("  Ground truth: not found")

    # Create visualization
    if visualize:
        vis_path = result_dir / f"{source_path.stem}.jpeg"
        create_visualization(source_path, boxes, gt_boxes, vis_path)
        print(f"  Visualization: {vis_path.name}")

    return len(boxes), len(gt_boxes)


def main():
    parser = argparse.ArgumentParser(
        description="Run face detection tests and generate visualizations"
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Process a specific image (optional, processes all if not specified)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=SOURCE_DIR,
        help=f"Directory containing source images (default: {SOURCE_DIR})",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=TARGET_DIR,
        help=f"Directory containing ground truth JSON (default: {TARGET_DIR})",
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=RESULT_DIR,
        help=f"Directory for output results (default: {RESULT_DIR})",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualizations with detected (green) and ground truth (cyan) boxes",
    )
    parser.add_argument(
        "--det-size",
        type=int,
        default=1280,
        help="Detection input size (default: 1280)",
    )

    args = parser.parse_args()

    det_size = (args.det_size, args.det_size)
    result_dir = args.result_dir
    result_dir.mkdir(exist_ok=True)

    print(f"Detection size: {det_size}")

    if args.image:
        # Process single image
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: Image not found: {image_path}")
            return 1
        process_image(image_path, args.target_dir, result_dir, det_size, args.visualize)
    else:
        # Process all images in source directory
        source_dir = args.source_dir
        if not source_dir.exists():
            print(f"Error: Source directory not found: {source_dir}")
            return 1

        image_extensions = {".jpg", ".jpeg", ".png"}
        images = [
            f
            for f in source_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        if not images:
            print(f"No images found in {source_dir}")
            return 1

        print(f"Processing {len(images)} images from {source_dir}")

        total_detected = 0
        total_gt = 0
        for image_path in sorted(images):
            detected, gt = process_image(
                image_path, args.target_dir, result_dir, det_size, args.visualize
            )
            total_detected += detected
            total_gt += gt

        print(f"\n{'='*50}")
        print(f"Total: {total_detected} faces detected, {total_gt} ground truth")

    return 0


if __name__ == "__main__":
    exit(main())
