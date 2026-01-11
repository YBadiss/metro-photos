"""
Face detection using RetinaFace (via InsightFace).

Detects faces in images and outputs bounding boxes in the same format
as the ground truth extraction script for comparison.
"""

import argparse
import json
from pathlib import Path

import cv2
from insightface.app import FaceAnalysis


# Default directories
SCRIPT_DIR = Path(__file__).parent
SOURCE_DIR = SCRIPT_DIR / "source"
RESULT_DIR = SCRIPT_DIR / "result"

# Global face analyzer (lazy initialization)
_face_analyzer = None
_current_det_size = None


def get_face_analyzer(det_size: tuple[int, int] = (640, 640)):
    """Get or initialize the face analyzer."""
    global _face_analyzer, _current_det_size
    if _face_analyzer is None or _current_det_size != det_size:
        # Initialize with RetinaFace detection model
        _face_analyzer = FaceAnalysis(
            name="buffalo_sc",  # Smaller model, good for detection
            allowed_modules=["detection"],  # Only load detection, not recognition
            providers=["CPUExecutionProvider"]
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
        List of bounding boxes as dicts with x, y, width, height
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # Get face analyzer
    app = get_face_analyzer(det_size=det_size)
    
    # Detect faces
    faces = app.get(img)
    
    bounding_boxes = []
    for face in faces:
        # bbox is [x1, y1, x2, y2]
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        confidence = float(face.det_score)
        
        bounding_boxes.append({
            "x": int(x1),
            "y": int(y1),
            "width": int(x2 - x1),
            "height": int(y2 - y1),
            "confidence": confidence
        })
    
    return bounding_boxes


def process_image(image_path: Path, result_dir: Path, det_size: tuple[int, int], visualize: bool) -> int:
    """Process a single image and save results."""
    print(f"\nDetecting faces in: {image_path.name}")
    
    boxes = detect_faces(str(image_path), det_size=det_size)
    
    print(f"  Found {len(boxes)} faces")
    for i, box in enumerate(boxes):
        print(f"    {i + 1}. x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}, conf={box['confidence']:.3f}")
    
    # Save JSON with same base name to result directory
    json_path = result_dir / f"{image_path.stem}.json"
    
    result = {
        "source_image": str(image_path.stem),
        "detector": "retinaface",
        "det_size": det_size[0],
        "boxes": boxes
    }
    
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"  Saved to: {json_path.name}")
    
    # Save visualization if requested
    if visualize:
        img = cv2.imread(str(image_path))
        for box in boxes:
            x, y, w, h = box["x"], box["y"], box["width"], box["height"]
            conf = box["confidence"]
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            label = f"{conf:.2f}"
            cv2.putText(img, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        vis_path = result_dir / f"{image_path.stem}.jpeg"
        cv2.imwrite(str(vis_path), img)
        print(f"  Visualization: {vis_path.name}")
    
    return len(boxes)


def main():
    parser = argparse.ArgumentParser(
        description="Detect faces using RetinaFace"
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to a specific image (optional, processes all source images if not specified)"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=SOURCE_DIR,
        help=f"Directory containing source images (default: {SOURCE_DIR})"
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=RESULT_DIR,
        help=f"Directory for output results (default: {RESULT_DIR})"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Save visualizations of detected faces"
    )
    parser.add_argument(
        "--det-size",
        type=int,
        default=1280,
        help="Detection input size (default: 1280). Larger = better for small faces but slower"
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
        process_image(image_path, result_dir, det_size, args.visualize)
    else:
        # Process all images in source directory
        source_dir = args.source_dir
        if not source_dir.exists():
            print(f"Error: Source directory not found: {source_dir}")
            return 1
        
        image_extensions = {".jpg", ".jpeg", ".png"}
        images = [f for f in source_dir.iterdir() 
                  if f.is_file() and f.suffix.lower() in image_extensions]
        
        if not images:
            print(f"No images found in {source_dir}")
            return 1
        
        print(f"Processing {len(images)} images from {source_dir}")
        
        total_faces = 0
        for image_path in sorted(images):
            total_faces += process_image(image_path, result_dir, det_size, args.visualize)
        
        print(f"\n{'='*50}")
        print(f"Total: {total_faces} faces detected from {len(images)} images")
    
    return 0


if __name__ == "__main__":
    exit(main())
