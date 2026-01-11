# Face Detection Testing

This folder contains tools for evaluating face detection algorithms against manually annotated ground truth.

## Folder Structure

```
app/back/
├── scripts/
│   └── detect_faces.py          # Core detection script (outputs JSON)
├── tests/
│   └── detection/
│       ├── source/              # Original photos for detection
│       ├── target/              # Photos with cyan bounding boxes + ground truth JSON
│       ├── result/              # Detection results (JSON + visualization images)
│       ├── run_detection_tests.py   # Test runner with visualization
│       ├── extract_targets.py   # Extract ground truth from annotated images
│       ├── evaluate.py          # Evaluate detection results
│       └── README.md
└── pyproject.toml
```

All files for the same photo share the same base name (e.g., `abbesses.jpeg`, `abbesses.json`).

## Scripts

### `scripts/detect_faces.py`

Core detection script. Detects faces in an image and outputs JSON.

```bash
# Output to stdout
uv run python scripts/detect_faces.py path/to/image.jpeg

# Output to file
uv run python scripts/detect_faces.py path/to/image.jpeg -o result.json
```

Options:
- `-o, --output FILE` - Output JSON file (default: stdout)
- `--det-size N` - Detection input size (default: 1280)

## Workflow

All commands should be run from the `app/back/` directory.

### 1. Annotate Ground Truth

Draw **cyan rectangles** (`#00FFFF`) around faces in each photo and save to `tests/detection/target/`.

Then extract the bounding boxes:

```bash
uv run python tests/detection/extract_targets.py
```

### 2. Run Detection Tests

Place original (unannotated) photos in `tests/detection/source/`, then run:

```bash
uv run python tests/detection/run_detection_tests.py --visualize
```

This will:
- Run face detection on all source images
- Save detection JSON to `result/`
- Generate visualizations showing detected boxes (green) over ground truth boxes (cyan)

Options:
- `--visualize` - Generate comparison visualizations
- `--det-size N` - Detection input size (default: 1280)

### 3. Evaluate Results

Compare detection results against ground truth using area coverage:

```bash
uv run python tests/detection/evaluate.py
```

Options:
- `-v` - Show detailed area information
- `abbesses` - Evaluate a single image by name

## Metrics

The evaluation uses **area-based coverage** rather than individual box matching.
This is appropriate for blurring use cases where we care about covering faces,
not matching exact bounding boxes.

- **Coverage** - What % of ground truth area is covered by detections (want high = faces get blurred)
- **Precision** - What % of detected area overlaps ground truth (some extra blur is acceptable)

## Detection Model

Uses RetinaFace via [InsightFace](https://github.com/deepinsight/insightface) (`buffalo_sc` model).
