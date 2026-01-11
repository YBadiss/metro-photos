"""
Evaluate face detection results against ground truth using area coverage.

For blurring use cases, we care about total area coverage rather than
individual box matching. This evaluation compares the union of all detected
boxes against the union of all ground truth boxes.
"""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


# Default directories
SCRIPT_DIR = Path(__file__).parent
TARGET_DIR = SCRIPT_DIR / "target"
RESULT_DIR = SCRIPT_DIR / "result"


def boxes_to_mask(boxes: list[dict], width: int, height: int) -> np.ndarray:
    """
    Create a binary mask from bounding boxes.

    Args:
        boxes: List of bounding boxes with x, y, width, height
        width: Image width
        height: Image height

    Returns:
        Binary mask where 1 = inside a box, 0 = outside
    """
    mask = np.zeros((height, width), dtype=np.uint8)

    for box in boxes:
        x1 = max(0, box["x"])
        y1 = max(0, box["y"])
        x2 = min(width, box["x"] + box["width"])
        y2 = min(height, box["y"] + box["height"])
        mask[y1:y2, x1:x2] = 1

    return mask


def evaluate_coverage(
    detected_boxes: list[dict],
    ground_truth_boxes: list[dict],
    image_width: int,
    image_height: int,
) -> dict:
    """
    Evaluate detection coverage using area comparison.

    Args:
        detected_boxes: List of detected bounding boxes
        ground_truth_boxes: List of ground truth bounding boxes
        image_width: Image width for mask creation
        image_height: Image height for mask creation

    Returns:
        Dict with coverage metrics
    """
    # Create masks
    gt_mask = boxes_to_mask(ground_truth_boxes, image_width, image_height)
    det_mask = boxes_to_mask(detected_boxes, image_width, image_height)

    # Calculate areas
    gt_area = np.sum(gt_mask)
    det_area = np.sum(det_mask)

    # Calculate overlap (intersection)
    overlap_mask = gt_mask & det_mask
    overlap_area = np.sum(overlap_mask)

    # Calculate missed area (ground truth not covered by detection)
    missed_mask = gt_mask & ~det_mask
    missed_area = np.sum(missed_mask)

    # Calculate extra area (detection outside ground truth)
    extra_mask = det_mask & ~gt_mask
    extra_area = np.sum(extra_mask)

    # Coverage: what fraction of ground truth is covered by detection
    coverage = overlap_area / gt_area if gt_area > 0 else 1.0

    # Precision: what fraction of detection overlaps with ground truth
    precision = overlap_area / det_area if det_area > 0 else 1.0

    return {
        "ground_truth_area": int(gt_area),
        "detected_area": int(det_area),
        "overlap_area": int(overlap_area),
        "missed_area": int(missed_area),
        "extra_area": int(extra_area),
        "coverage": coverage,  # Recall-like: GT covered by detection
        "precision": precision,  # Detection that overlaps GT
    }


def get_image_dimensions(image_name: str, source_dir: Path) -> tuple[int, int]:
    """Get image dimensions from source directory."""
    for ext in [".jpeg", ".jpg", ".png"]:
        image_path = source_dir / f"{image_name}{ext}"
        if image_path.exists():
            img = cv2.imread(str(image_path))
            if img is not None:
                return img.shape[1], img.shape[0]  # width, height

    # Fallback: try to get from target directory
    target_dir = source_dir.parent / "target"
    for ext in [".jpeg", ".jpg", ".png"]:
        image_path = target_dir / f"{image_name}{ext}"
        if image_path.exists():
            img = cv2.imread(str(image_path))
            if img is not None:
                return img.shape[1], img.shape[0]

    # Default fallback
    return 4000, 3000


def evaluate_single(
    detected_path: Path, ground_truth_path: Path, source_dir: Path
) -> dict:
    """Evaluate detection results for a single image."""
    with open(detected_path) as f:
        detected_data = json.load(f)

    with open(ground_truth_path) as f:
        gt_data = json.load(f)

    detected_boxes = detected_data["boxes"]
    gt_boxes = gt_data["boxes"]

    # Get image dimensions
    image_name = detected_path.stem
    width, height = get_image_dimensions(image_name, source_dir)

    # Evaluate coverage
    metrics = evaluate_coverage(detected_boxes, gt_boxes, width, height)
    metrics["image"] = image_name
    metrics["ground_truth_count"] = len(gt_boxes)
    metrics["detected_count"] = len(detected_boxes)

    return metrics


def print_single_result(result: dict, verbose: bool = False):
    """Print evaluation results for a single image."""
    print(f"\n{result['image']}:")
    print(
        f"  Boxes: {result['detected_count']} detected, {result['ground_truth_count']} ground truth"
    )
    print(f"  Coverage: {result['coverage']:.1%} of ground truth area covered")
    print(f"  Precision: {result['precision']:.1%} of detected area is on target")

    if verbose:
        print(
            f"  Areas: GT={result['ground_truth_area']:,}px, Det={result['detected_area']:,}px, "
            f"Overlap={result['overlap_area']:,}px"
        )
        if result["missed_area"] > 0:
            print(
                f"  Missed: {result['missed_area']:,}px ({result['missed_area']/result['ground_truth_area']:.1%} of GT)"
            )
        if result["extra_area"] > 0:
            print(f"  Extra: {result['extra_area']:,}px")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate face detection results using area coverage"
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Base name of files to evaluate (e.g., 'abbesses'). If not specified, evaluates all.",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=TARGET_DIR,
        help=f"Directory containing ground truth JSON files (default: {TARGET_DIR})",
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=RESULT_DIR,
        help=f"Directory containing detection result JSON files (default: {RESULT_DIR})",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=SCRIPT_DIR / "source",
        help="Directory containing source images (for dimensions)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed area information"
    )

    args = parser.parse_args()

    target_dir = args.target_dir
    result_dir = args.result_dir

    if not target_dir.exists():
        print(f"Error: Target directory not found: {target_dir}")
        return 1

    if not result_dir.exists():
        print(f"Error: Result directory not found: {result_dir}")
        return 1

    if args.name:
        # Evaluate single image
        detected_path = result_dir / f"{args.name}.json"
        gt_path = target_dir / f"{args.name}.json"

        if not detected_path.exists():
            print(f"Error: Detection result not found: {detected_path}")
            return 1
        if not gt_path.exists():
            print(f"Error: Ground truth not found: {gt_path}")
            return 1

        result = evaluate_single(detected_path, gt_path, args.source_dir)
        print_single_result(result, args.verbose)
    else:
        # Evaluate all images
        gt_files = list(target_dir.glob("*.json"))
        if not gt_files:
            print(f"No ground truth JSON files found in {target_dir}")
            return 1

        results = []
        total_gt_area = 0
        total_det_area = 0
        total_overlap_area = 0
        total_missed_area = 0
        total_extra_area = 0

        for gt_path in sorted(gt_files):
            detected_path = result_dir / gt_path.name

            if not detected_path.exists():
                print(f"\nSkipping {gt_path.stem}: no detection result found")
                continue

            result = evaluate_single(detected_path, gt_path, args.source_dir)
            results.append(result)
            print_single_result(result, args.verbose)

            total_gt_area += result["ground_truth_area"]
            total_det_area += result["detected_area"]
            total_overlap_area += result["overlap_area"]
            total_missed_area += result["missed_area"]
            total_extra_area += result["extra_area"]

        if results:
            # Calculate aggregate metrics
            total_coverage = (
                total_overlap_area / total_gt_area if total_gt_area > 0 else 1.0
            )
            total_precision = (
                total_overlap_area / total_det_area if total_det_area > 0 else 1.0
            )

            print(f"\n{'='*60}")
            print("AGGREGATE RESULTS")
            print(f"{'='*60}")
            print(f"Images evaluated: {len(results)}")
            print(f"Total ground truth area: {total_gt_area:,} px")
            print(f"Total detected area: {total_det_area:,} px")
            print(f"Total overlap: {total_overlap_area:,} px")
            print()
            print(f"Coverage: {total_coverage:.1%} of faces will be blurred")
            print(f"Precision: {total_precision:.1%} of blur is on faces")
            if total_missed_area > 0:
                print(
                    f"Missed: {total_missed_area:,} px ({total_missed_area/total_gt_area:.1%} of faces NOT blurred)"
                )
            print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    exit(main())
