"""
Evaluate face detection results against ground truth.

Compares detected bounding boxes with ground truth boxes using IoU
(Intersection over Union) metric and calculates precision/recall.
"""

import argparse
import json
from pathlib import Path


# Default directories
SCRIPT_DIR = Path(__file__).parent
TARGET_DIR = SCRIPT_DIR / "target"
RESULT_DIR = SCRIPT_DIR / "result"


def calculate_iou(box1: dict, box2: dict) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1, box2: Dicts with x, y, width, height
        
    Returns:
        IoU value between 0 and 1
    """
    # Convert to x1, y1, x2, y2 format
    x1_1, y1_1 = box1["x"], box1["y"]
    x2_1, y2_1 = x1_1 + box1["width"], y1_1 + box1["height"]
    
    x1_2, y1_2 = box2["x"], box2["y"]
    x2_2, y2_2 = x1_2 + box2["width"], y1_2 + box2["height"]
    
    # Calculate intersection
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Calculate union
    area1 = box1["width"] * box1["height"]
    area2 = box2["width"] * box2["height"]
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def match_boxes(
    detected: list[dict],
    ground_truth: list[dict],
    iou_threshold: float = 0.5
) -> tuple[list[tuple], list[int], list[int]]:
    """
    Match detected boxes to ground truth boxes using IoU.
    
    Args:
        detected: List of detected bounding boxes
        ground_truth: List of ground truth bounding boxes
        iou_threshold: Minimum IoU to consider a match
        
    Returns:
        Tuple of:
        - matches: List of (detected_idx, gt_idx, iou) tuples
        - unmatched_detected: List of indices of false positives
        - unmatched_gt: List of indices of missed ground truth (false negatives)
    """
    matches = []
    matched_gt = set()
    matched_det = set()
    
    # Calculate all IoU pairs
    iou_pairs = []
    for i, det_box in enumerate(detected):
        for j, gt_box in enumerate(ground_truth):
            iou = calculate_iou(det_box, gt_box)
            if iou >= iou_threshold:
                iou_pairs.append((iou, i, j))
    
    # Sort by IoU descending and greedily match
    iou_pairs.sort(reverse=True)
    
    for iou, det_idx, gt_idx in iou_pairs:
        if det_idx not in matched_det and gt_idx not in matched_gt:
            matches.append((det_idx, gt_idx, iou))
            matched_det.add(det_idx)
            matched_gt.add(gt_idx)
    
    # Find unmatched
    unmatched_detected = [i for i in range(len(detected)) if i not in matched_det]
    unmatched_gt = [i for i in range(len(ground_truth)) if i not in matched_gt]
    
    return matches, unmatched_detected, unmatched_gt


def evaluate_single(
    detected_path: Path,
    ground_truth_path: Path,
    iou_threshold: float = 0.5
) -> dict:
    """
    Evaluate detection results against ground truth for a single image.
    
    Args:
        detected_path: Path to JSON with detected boxes
        ground_truth_path: Path to JSON with ground truth boxes
        iou_threshold: Minimum IoU to consider a match
        
    Returns:
        Dict with evaluation metrics
    """
    with open(detected_path) as f:
        detected_data = json.load(f)
    
    with open(ground_truth_path) as f:
        gt_data = json.load(f)
    
    detected = detected_data["boxes"]
    ground_truth = gt_data["boxes"]
    
    matches, false_positives, false_negatives = match_boxes(
        detected, ground_truth, iou_threshold
    )
    
    # Calculate metrics
    true_positives = len(matches)
    num_false_positives = len(false_positives)
    num_false_negatives = len(false_negatives)
    
    precision = true_positives / (true_positives + num_false_positives) if (true_positives + num_false_positives) > 0 else 0
    recall = true_positives / (true_positives + num_false_negatives) if (true_positives + num_false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # Average IoU of matches
    avg_iou = sum(m[2] for m in matches) / len(matches) if matches else 0
    
    return {
        "image": detected_path.stem,
        "iou_threshold": iou_threshold,
        "ground_truth_count": len(ground_truth),
        "detected_count": len(detected),
        "true_positives": true_positives,
        "false_positives": num_false_positives,
        "false_negatives": num_false_negatives,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "average_iou": avg_iou,
        "matches": [
            {
                "detected_idx": m[0],
                "ground_truth_idx": m[1],
                "iou": m[2],
                "detected_box": detected[m[0]],
                "ground_truth_box": ground_truth[m[1]]
            }
            for m in matches
        ],
        "false_positive_boxes": [detected[i] for i in false_positives],
        "false_negative_boxes": [ground_truth[i] for i in false_negatives]
    }


def print_single_result(result: dict, verbose: bool = False):
    """Print evaluation results for a single image."""
    print(f"\n{result['image']}:")
    print(f"  GT: {result['ground_truth_count']}, Det: {result['detected_count']}, "
          f"TP: {result['true_positives']}, FP: {result['false_positives']}, FN: {result['false_negatives']}")
    print(f"  Precision: {result['precision']:.1%}, Recall: {result['recall']:.1%}, "
          f"F1: {result['f1_score']:.1%}, Avg IoU: {result['average_iou']:.1%}")
    
    if verbose:
        if result['false_positive_boxes']:
            print(f"  False positives: {len(result['false_positive_boxes'])}")
        if result['false_negative_boxes']:
            print(f"  False negatives: {len(result['false_negative_boxes'])}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate face detection results against ground truth"
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Base name of files to evaluate (e.g., 'abbesses'). If not specified, evaluates all."
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=TARGET_DIR,
        help=f"Directory containing ground truth JSON files (default: {TARGET_DIR})"
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=RESULT_DIR,
        help=f"Directory containing detection result JSON files (default: {RESULT_DIR})"
    )
    parser.add_argument(
        "--iou-threshold",
        type=float,
        default=0.5,
        help="Minimum IoU to consider a match (default: 0.5)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed results"
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
    
    print(f"IoU threshold: {args.iou_threshold}")
    
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
        
        result = evaluate_single(detected_path, gt_path, args.iou_threshold)
        print_single_result(result, args.verbose)
    else:
        # Evaluate all images
        gt_files = list(target_dir.glob("*.json"))
        if not gt_files:
            print(f"No ground truth JSON files found in {target_dir}")
            return 1
        
        results = []
        total_gt = 0
        total_det = 0
        total_tp = 0
        total_fp = 0
        total_fn = 0
        
        for gt_path in sorted(gt_files):
            detected_path = result_dir / gt_path.name
            
            if not detected_path.exists():
                print(f"\nSkipping {gt_path.stem}: no detection result found")
                continue
            
            result = evaluate_single(detected_path, gt_path, args.iou_threshold)
            results.append(result)
            print_single_result(result, args.verbose)
            
            total_gt += result["ground_truth_count"]
            total_det += result["detected_count"]
            total_tp += result["true_positives"]
            total_fp += result["false_positives"]
            total_fn += result["false_negatives"]
        
        if results:
            # Calculate aggregate metrics
            precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
            recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            print(f"\n{'='*60}")
            print("AGGREGATE RESULTS")
            print(f"{'='*60}")
            print(f"Images evaluated: {len(results)}")
            print(f"Total ground truth faces: {total_gt}")
            print(f"Total detected faces: {total_det}")
            print(f"True Positives: {total_tp}")
            print(f"False Positives: {total_fp}")
            print(f"False Negatives: {total_fn}")
            print(f"\nPrecision: {precision:.1%}")
            print(f"Recall:    {recall:.1%}")
            print(f"F1 Score:  {f1:.1%}")
            print(f"{'='*60}")
    
    return 0


if __name__ == "__main__":
    exit(main())
