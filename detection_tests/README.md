# Face Detection Testing

This folder contains tools for evaluating face detection algorithms against manually annotated ground truth.

## Folder Structure

```
detection_tests/
├── source/          # Original photos for detection
├── target/          # Photos with cyan bounding boxes + ground truth JSON
├── result/          # Detection results (JSON + visualization images)
├── extract_targets.py
├── detect_faces.py
├── evaluate.py
└── pyproject.toml
```

All files for the same photo share the same base name (e.g., `abbesses.jpeg`, `abbesses.json`).

## Workflow

### 1. Annotate Ground Truth

Draw **cyan rectangles** (`#00FFFF`) around faces in each photo and save to `target/`.

Then extract the bounding boxes:

```bash
uv run python extract_targets.py
```

This reads all images from `target/` and creates corresponding JSON files with bounding box coordinates.

### 2. Run Face Detection

Place original (unannotated) photos in `source/`, then run:

```bash
uv run python detect_faces.py --visualize
```

Options:
- `--det-size N` - Detection input size (default: 1280). Larger values detect smaller faces but run slower.
- `--visualize` - Save images with detection boxes drawn

Results are saved to `result/`.

### 3. Evaluate Results

Compare detection results against ground truth:

```bash
uv run python evaluate.py
```

Options:
- `--iou-threshold N` - Minimum IoU to consider a match (default: 0.5, try 0.3 for looser matching)
- `-v` - Verbose output with false positive/negative details
- `abbesses` - Evaluate a single image by name

## Metrics

- **Precision** - What fraction of detections are correct
- **Recall** - What fraction of ground truth faces were detected
- **F1 Score** - Harmonic mean of precision and recall
- **IoU** - Intersection over Union, measures box overlap quality

## Detection Model

Uses RetinaFace via [InsightFace](https://github.com/deepinsight/insightface) (`buffalo_sc` model).
