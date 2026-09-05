# PalletDataGenerator

[![PyPI version](https://badge.fury.io/py/palletdatagenerator.svg)](https://badge.fury.io/py/palletdatagenerator)
[![Build Status](https://github.com/boubakriibrahim/PalletDataGenerator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/boubakriibrahim/PalletDataGenerator/actions)
[![Coverage Status](https://coveralls.io/repos/github/boubakriibrahim/PalletDataGenerator/badge.svg?branch=main)](https://coveralls.io/github/boubakriibrahim/PalletDataGenerator?branch=main)
[![Documentation Status](https://img.shields.io/badge/docs-GitHub%20Pages-blue?logo=github)](https://boubakriibrahim.github.io/PalletDataGenerator)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/palletdatagenerator.svg)](https://pypistats.org/packages/palletdatagenerator)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.5+](https://img.shields.io/badge/blender-4.5+-orange.svg)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **A professional Python library for generating high-quality synthetic pallet datasets using Blender for computer vision and machine learning applications.**

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [System Architecture](#system-architecture)
- [Generation Modes](#generation-modes)
- [Multi-Modal Output](#multi-modal-output)
- [Keypoints Generation](#keypoints-generation)
- [Annotation Formats](#annotation-formats)
- [Rendering Pipeline](#rendering-pipeline)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Blender Scene Requirements](#blender-scene-requirements)
- [Output Structure](#output-structure)
- [Integration with PalletDetection](#integration-with-palletdetection)
- [API Reference](#api-reference)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License & Citation](#license--citation)

---

## Overview

PalletDataGenerator is a production-ready solution for creating photorealistic synthetic datasets of pallets and warehouse environments. It uses **Blender Cycles** as the rendering engine with GPU acceleration (CUDA, OptiX, Metal, HIP) to generate multi-modal training data for object detection, keypoint estimation, and 6D pose estimation models.

### Key Features

- **Dual Generation Modes**: Single pallet focus and complex multi-pallet warehouse scenarios
- **Multi-Modal Output**: RGB, depth maps (16-bit), normal maps, and index/segmentation maps per frame
- **Advanced Keypoints**: Automatic face detection with 6 keypoints per face, visibility tracking via ray casting, 3D debug visualization
- **Multiple Annotation Formats**: YOLO, COCO JSON, and PASCAL VOC XML
- **GPU-Accelerated Rendering**: Auto-detects CUDA/OptiX/Metal/HIP backends with configurable denoising
- **Batch Management**: Auto-incrementing `generated_XXXXXX` folders with dataset manifests
- **Pallet Stacking**: Configurable probability-based vertical stacking with gap control
- **Professional CLI**: Full command-line interface with `palletgen` entry point

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Blender 4.5+** (automatically detected or specify path)
- **GPU recommended**: NVIDIA (CUDA/OptiX), Apple Silicon (Metal), or AMD (HIP)

### Installation

```bash
# From PyPI (recommended)
pip install palletdatagenerator

# From source
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator
pip install -e .
```

### Basic Usage

```bash
# Single pallet dataset (default mode)
palletgen scenes/one_pallet.blend --frames 100

# Warehouse dataset with multiple pallets
palletgen scenes/warehouse_objects.blend --mode warehouse --frames 50

# High-resolution with custom output
palletgen scenes/one_pallet.blend -f 200 -r 1920 1080 -o output/highres

# With pallet stacking and debug visualization
palletgen scenes/one_pallet.blend --stacked-pallets 0.6 --debug --debug-3d
```

---

## System Architecture

```
+------------------------------------------------------------------+
|                      PalletDataGenerator                          |
+------------------------------------------------------------------+
|                                                                    |
|  CLI (cli.py)                                                      |
|    |                                                               |
|    v                                                               |
|  PalletDataGenerator (generator.py)  <--- Config (config.py)      |
|    |                                                               |
|    v                                                               |
|  BlenderRunner (blender_runner.py)                                 |
|    |  Launches Blender as subprocess                               |
|    |  Passes config via environment/args                           |
|    v                                                               |
|  +------------------------------------------------------------+   |
|  |  Blender Python Environment (bpy)                           |   |
|  |                                                              |   |
|  |  BaseGenerator (modes/base_generator.py)                     |   |
|  |    - GPU backend detection & setup                           |   |
|  |    - Render configuration (Cycles engine)                    |   |
|  |    - Compositor nodes (depth, normals, index passes)         |   |
|  |    - Lighting setup (randomized per frame)                   |   |
|  |    - Floor & environment creation                            |   |
|  |    - Annotation export (YOLO, COCO, VOC)                    |   |
|  |       |                        |                             |   |
|  |       v                        v                             |   |
|  |  SinglePalletMode         WarehouseMode                      |   |
|  |  (single_pallet.py)      (warehouse.py)                      |   |
|  |    - Spherical camera      - Forklift camera path            |   |
|  |    - Side face focus       - Multi-pallet coordination       |   |
|  |    - Stack variations      - Dynamic box stacking            |   |
|  |                            - Scene randomization             |   |
|  |                                                              |   |
|  |  VisibilityUtils (visibility_utils.py)                       |   |
|  |    - Face detection from mesh geometry                       |   |
|  |    - Ray casting for occlusion testing                       |   |
|  |    - Keypoint generation (6 per face)                        |   |
|  +------------------------------------------------------------+   |
|                                                                    |
|  Output: images/ depth/ normals/ index/ yolo_labels/              |
|          keypoints_labels/ coco/ voc_xml/ debug_3d/ analysis/     |
+------------------------------------------------------------------+
```

### Module Responsibilities

| Module | Lines | Purpose |
|--------|-------|---------|
| `cli.py` | ~644 | Argument parsing, Blender process management |
| `config.py` | ~309 | Configuration dataclasses, auto-batch folder naming |
| `generator.py` | ~774 | Main orchestrator, dependency validation |
| `blender_runner.py` | ~443 | Blender environment setup, asset loading |
| `base_generator.py` | ~3236 | GPU setup, rendering, compositor, lighting, annotation export |
| `single_pallet.py` | ~1537 | Camera positioning, single pallet frame generation |
| `warehouse.py` | ~5250 | Forklift simulation, multi-pallet scenes, camera paths |
| `visibility_utils.py` | ~934 | Face detection, ray casting, occlusion testing |
| `utils.py` | ~418 | Logging, dataset verification, manifests |

---

## Generation Modes

### Single Pallet Mode

Generates focused images of individual pallets with controlled camera positioning.

**Camera Strategy:**
- 90% probability: Side face focus (front/back/left/right with configurable angle ranges)
- 10% probability: Random viewpoint
- Distance: 1.8 - 4.0 Blender units
- Elevation: -5 to +35 degrees (prevents extreme low angles)
- Ground safety: Camera clamped above minimum Z threshold

**Features:**
- Controlled backgrounds for clean training data
- Pallet stacking variations (probability-based)
- Material/texture randomization
- Per-frame lighting variation

```bash
palletgen scenes/one_pallet.blend \
  --frames 200 \
  --resolution 1024 768 \
  --stacked-pallets 0.5 \
  --stacked-pallets-max 3
```

### Warehouse Mode

Generates complex multi-pallet warehouse scenes with simulated forklift camera movement.

**Camera Strategy:**
- Simulates forklift-mounted camera path through warehouse
- Camera height: 1.4 - 2.0 meters (realistic forklift height)
- Forward step: 0.3 - 0.8 meters between frames
- Lateral and angular jitter for realism
- Multiple scenes with 15 frames each

**Features:**
- Multiple pallets with varying positions and orientations
- Dynamic box visibility randomization (box1, box2, box3 templates)
- Complex occlusion scenarios
- Realistic warehouse lighting

```bash
palletgen scenes/warehouse_objects.blend \
  --mode warehouse \
  --frames 50 \
  --resolution 1920 1080
```

---

## Multi-Modal Output

Each rendered frame produces four image modalities:

| Modality | Format | Description |
|----------|--------|-------------|
| **RGB** | PNG (8-bit) | Photorealistic rendered image |
| **Depth** | PNG (16-bit) | Distance from camera in mm (scaled by 1000.0) |
| **Normals** | PNG (RGB 8-bit) | Surface normal vectors, mapped from [-1,1] to [0,255] |
| **Index** | PNG (8-bit grayscale) | Object instance segmentation mask |

### Example Outputs

**Warehouse Mode:**

<div align="center">
<img src="readme_images/examples/warehouse_example_1.png" width="400" alt="Warehouse Example 1">
<img src="readme_images/examples/warehouse_example_2.png" width="400" alt="Warehouse Example 2">
</div>

**Single Pallet Mode:**

<div align="center">
<img src="readme_images/examples/single_pallet_example_1.png" width="400" alt="Single Pallet Example 1">
<img src="readme_images/examples/single_pallet_example_2.png" width="400" alt="Single Pallet Example 2">
</div>

**Multi-Modal Comparison:**

| RGB Image | Analysis Overlay | Depth Map | Normal Map |
|-----------|------------------|-----------|------------|
| <img src="readme_images/outputs/single_pallet_example.png" width="200"> | <img src="readme_images/outputs/analysis_example.png" width="200"> | <img src="readme_images/outputs/depth_example.png" width="200"> | <img src="readme_images/outputs/normal_example.png" width="200"> |
| <img src="readme_images/outputs/warehouse_example.png" width="200"> | <img src="readme_images/outputs/analysis_example_2.png" width="200"> | <img src="readme_images/outputs/warehouse_depth_example.png" width="200"> | <img src="readme_images/outputs/warehouse_normal_example.png" width="200"> |

---

## Keypoints Generation

The system automatically detects pallet faces and generates precise keypoints for pose estimation training.

### Face Detection Algorithm

1. Scan scene for objects containing "face" in their name
2. Extract mesh geometry and identify side faces from 3D bounding box
3. Project faces to 2D image space
4. Calculate visible area and orientation relative to camera
5. Select the **1-2 most visible faces** (by area, distance, and camera angle)

### Keypoint Layout (6 per face)

```
Top-Left (2)      Middle-Top (0)      Top-Right (4)
     *                  *                  *
     |                  |                  |
     |                  |                  |
Bottom-Left (3)  Middle-Bottom (1)  Bottom-Right (5)
     *                  *                  *
```

### Visibility Tracking

Each keypoint has a visibility flag determined by ray casting:
- **0** = Hidden (ray hits obstacle before reaching keypoint)
- **2** = Visible (unobstructed line of sight from camera)

### 3D Debug Visualization

Enable with `--debug-3d` to generate interactive HTML files (Plotly.js):

| Feature | Representation |
|---------|---------------|
| Pallet corners | Red diamonds (8 corners) |
| Camera position | Blue diamond |
| Camera-to-corner distances | Gray dashed lines |
| Selected faces | Green/Orange highlighting |
| Keypoints | Colored markers on selected faces |

| Original Image | Keypoints Analysis | 3D Debug Visualization |
|----------------|-------------------|------------------------|
| <img src="readme_images/examples/single_pallet_keypoints_example.png" width="200"> | <img src="readme_images/outputs/keypoints_analysis_example.png" width="200"> | <img src="readme_images/outputs/debug_3d_example.png" width="200"> |

```bash
# Generate with debug output
palletgen scenes/one_pallet.blend --debug --debug-3d -f 10

# View interactive 3D visualization
open output/single_pallet/generated_XXXXXX/debug_3d/figures/frame_000000_3d_interactive.html

# View coordinate details
cat output/single_pallet/generated_XXXXXX/debug_3d/coordinates/frame_000000_coordinates.txt
```

---

## Annotation Formats

### YOLO Format (`yolo_labels/`)

```
<class_id> <x_center> <y_center> <width> <height>
```

Example:
```
0 0.475345 0.595753 0.247050 0.102537
```

All values normalized to [0, 1] relative to image dimensions.

### Keypoints YOLO Format (`keypoints_labels/`)

```
<class_id> <x_c> <y_c> <w> <h> <kp1_x> <kp1_y> <kp1_v> <kp2_x> <kp2_y> <kp2_v> ... <kp6_x> <kp6_y> <kp6_v>
```

Example (6 keypoints for one face):
```
0 0.573150 0.639442 0.284453 0.139362 0.580366 0.603590 2 0.578420 0.669213 2 0.715376 0.569761 2 0.710409 0.633069 2 0.430924 0.641035 2 0.432683 0.709123 2
```

Visibility: `2` = visible, `0` = hidden

### COCO JSON Format (`coco/`)

```json
{
  "info": {"description": "PalletDataGenerator synthetic dataset"},
  "images": [
    {"id": 1, "file_name": "000000.png", "width": 640, "height": 640}
  ],
  "annotations": [
    {
      "id": 1, "image_id": 1, "category_id": 1,
      "bbox": [x, y, width, height],
      "area": 40000, "iscrowd": 0
    }
  ],
  "categories": [
    {"id": 1, "name": "pallet", "supercategory": "object"}
  ]
}
```

### PASCAL VOC XML Format (`voc_xml/`)

```xml
<annotation>
  <filename>000000.png</filename>
  <size><width>640</width><height>640</height><depth>3</depth></size>
  <object>
    <name>pallet</name>
    <bndbox>
      <xmin>123</xmin><ymin>456</ymin>
      <xmax>789</xmax><ymax>654</ymax>
    </bndbox>
  </object>
</annotation>
```

---

## Rendering Pipeline

### GPU Backend Selection (Priority Order)

1. User preference via `PALLET_GPU_BACKEND` environment variable
2. **CUDA** (NVIDIA GPUs - preferred for compute clusters)
3. **OptiX** (NVIDIA RTX cards - fast denoising)
4. **Metal** (Apple Silicon)
5. **HIP** (AMD GPUs)
6. **OpenCL** (Fallback)

### Performance Optimizations

| Setting | Value | Purpose |
|---------|-------|---------|
| Tile size | 256x256 | Maximize GPU VRAM utilization |
| Max bounces | 2 | Minimize render time |
| Denoiser | OptiX / OpenImageDenoise | Clean output with low samples |
| Adaptive sampling | Enabled (fast mode) | Skip converged pixels |
| Persistent data | Enabled | Reuse data between frames |
| Fast GI | Enabled | GPU-accelerated global illumination |
| Caustics | Disabled | Not needed for pallet scenes |
| Samples | 8 (fast) / 128 (quality) | Trade speed vs quality |

### Compositor Nodes

Blender's compositor is configured to extract multiple render passes:

```
Render Layers
  |--- Combined (RGB) ---------> File Output (images/)
  |--- Depth -------> Normalize -> Map Range -> File Output (depth/)
  |--- Normal ------> Map [-1,1] to [0,255] -> File Output (normals/)
  |--- IndexOB -----> File Output (index/)
```

---

## Configuration

### Embedded Default Configs

The system ships with production-tested defaults for both modes:

```python
# Single Pallet defaults
{
    "num_images": 50,
    "resolution_x": 640,
    "resolution_y": 640,
    "render_engine": "CYCLES",
    "camera_focal_mm": 35.0,
    "side_face_probability": 0.9,
    "allow_cropping": True,
    "min_visible_area_ratio": 0.3,
    "add_floor": True,
    "depth_scale": 1000.0,
    "generate_keypoints": True,
    "keypoints_min_face_area": 80,
    "stacked_pallets_probability": 0.5,
    "fast_samples": 8,
}

# Warehouse defaults
{
    "num_images": 50,
    "num_scenes": 3,
    "max_images_per_scene": 15,
    "camera_height_range_m": [1.4, 2.0],
    "camera_forward_step_m": [0.3, 0.8],
    "max_boxes_per_pallet": 8,
    "stacking_probability": 0.7,
    "lighting_variations": True,
    "generate_keypoints": True,
}
```

### Override Priority

```
Embedded defaults --> YAML/JSON config file --> CLI arguments (highest priority)
```

---

## CLI Reference

```
palletgen <scene_path> [OPTIONS]

Positional Arguments:
  scene_path                       Path to .blend file (required)

Mode & Output:
  -m, --mode {single_pallet,warehouse}    Generation mode (default: single_pallet)
  -f, --frames N                          Number of frames to generate (default: 50)
  -r, --resolution WIDTH HEIGHT           Image resolution (default: 640 640)
  -o, --output DIR                        Output directory (default: output/{mode}/generated_XXXXXX)

Pallet Stacking:
  --stacked-pallets PROB           Probability 0..1 for stacking (default: disabled)
  --stacked-pallets-max N          Max pallets in stack (default: 5)
  --pallet-stack-vertical          Stack vertically (default)
  --no-pallet-stack-vertical       Stack horizontally (X/Y)
  --pallet-stack-gap GAP           Gap between stacked pallets (Blender units)

Debug:
  --debug                          Enable debug logging
  --debug-3d                       Generate debug_3d/ visualization folder
```

---

## Blender Scene Requirements

### Single Pallet Scene (`scenes/one_pallet.blend`)

**Required objects:**
- `pallet` - Mesh object representing the pallet (must have applied transforms)

**Optional objects:**
- `box` - Non-annotated helper object (moves with pallet)
- `box1`, `box2`, `box3` - Template objects for box stacking variations
- Face objects (named with "face" prefix) - Used for keypoint generation

**Guidelines:**
- Apply all transforms (`Ctrl+A` -> All Transforms in Blender)
- Use metric units (meters)
- Origin at world center recommended

### Warehouse Scene (`scenes/warehouse_objects.blend`)

**Required objects:**
- `box1`, `box2`, `box3` - Box template objects (must exist and be visible initially)
- Pallet objects - Named with "pallet" prefix or grouped in collections

**Scene structure:**
- Pallets optionally grouped in collections (e.g., `Column.001`)
- Box variants are randomly toggled per frame
- Camera path is computed dynamically through the scene

---

## Output Structure

Each generation batch creates an auto-incrementing folder:

```
output/
├── single_pallet/
│   └── generated_000001/
│       ├── images/                  # RGB rendered images (PNG)
│       ├── depth/                   # 16-bit depth maps (PNG, mm)
│       ├── normals/                 # Normal maps (RGB PNG)
│       ├── index/                   # Object index segmentation (8-bit PNG)
│       ├── analysis/               # Overlay images with keypoints & boxes
│       ├── yolo_labels/            # YOLO format bounding boxes
│       ├── keypoints_labels/       # YOLO format with 6 keypoints per face
│       ├── face_2d_boxes/          # 2D bounding boxes for detected faces
│       ├── face_2d_keypoints/      # Face keypoints (alternate storage)
│       ├── face_3d_coordinates/    # 3D world coordinates of keypoints
│       ├── coco/                   # COCO JSON annotations
│       ├── voc_xml/                # PASCAL VOC XML annotations (optional)
│       ├── debug_3d/               # 3D debug visualization (if --debug-3d)
│       │   ├── figures/            #   Interactive HTML (Plotly.js)
│       │   ├── coordinates/        #   Detailed coordinate text files
│       │   └── images/             #   Static 3D visualization PNGs
│       ├── dataset_manifest.json   # Generation metadata & parameters
│       └── annotations_coco.json   # COCO format dataset file
│
└── warehouse/
    └── generated_000001/           # Same structure as above
```

---

## Integration with PalletDetection

PalletDataGenerator is the companion project to [PalletDetection](https://github.com/boubakriibrahim/PalletDetection), providing synthetic training data for the detection and pose estimation pipeline.

### Data Flow

```
PalletDataGenerator                        PalletDetection
(Blender Rendering)                        (ML Training & Deployment)
                                          
  RGB images --------+                     
  Depth maps --------+                     
  Normal maps -------+---> dataset/ -----> Training Pipeline (YOLO v8-v11)
  YOLO labels -------+                         |
  Keypoints labels --+                     Trained Model (.pt / .onnx)
                                               |
                                           FastAPI + React Web App
```

### Supported Training Channels

| Configuration | Channels | Input Data |
|--------------|----------|------------|
| Standard RGB | 3 | `images/` only |
| RGB + Depth | 4 | `images/` + `depth/` |
| RGB + Normals | 6 | `images/` + `normals/` |
| RGB + Depth + Normals | 7 | `images/` + `depth/` + `normals/` |

See [4channel_walkthrough.md](4channel_walkthrough.md) for detailed RGBD integration instructions.

### Preparing Data for Training

```bash
# 1. Generate synthetic data
palletgen scenes/one_pallet.blend -f 500 -r 640 640

# 2. Organize into YOLO structure for PalletDetection
# output/single_pallet/generated_XXXXXX/
#   images/ -> dataset/images/train/
#   yolo_labels/ -> dataset/labels/train/
#   (or keypoints_labels/ for pose training)

# 3. Train in PalletDetection
cd ../PalletDetection
python core/scripts/train.py --model_type yolov8 --mode detection \
  --data-dir /path/to/dataset --epochs 100
```

---

## API Reference

### Core Classes

#### `PalletDataGenerator` (generator.py)

Main orchestrator that validates dependencies and dispatches to mode-specific generators.

```python
from palletdatagenerator import PalletDataGenerator

generator = PalletDataGenerator(
    scene_path="scenes/warehouse_objects.blend",
    mode="warehouse",
    output_dir="custom_output"
)
generator.generate_dataset(num_frames=100)
```

#### Mode Generators

```python
from palletdatagenerator.modes import WarehouseMode, SinglePalletMode

# Direct mode usage (inside Blender Python)
warehouse = WarehouseMode(config=custom_config)
warehouse.generate_scene(frame_number=0)

single = SinglePalletMode(config=custom_config)
single.generate_scene(frame_number=0)
```

#### Utility Functions

```python
from palletdatagenerator.utils import (
    find_blender_executable,
    setup_logging,
    validate_scene_file
)

blender_path = find_blender_executable()  # Auto-detect Blender
is_valid = validate_scene_file("path/to/scene.blend")
```

---

## Development Setup

### Installation

```bash
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Development install with all extras
pip install -e ".[dev,docs,test]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality

```bash
black src/ tests/                             # Format code
ruff check src/ tests/                        # Lint
mypy src/                                     # Type check
pytest --cov=palletdatagenerator --cov-report=html  # Test + coverage
bandit -r src/                                # Security scan
```

### Documentation

```bash
cd docs && make html
# Output: docs/_build/html/index.html
```

### Docker

```bash
# Development image with Blender
docker build --target development -t palletgen:dev .

# Run generation
docker run -v $(pwd)/output:/home/pallet/app/output palletgen:dev \
  palletgen scenes/one_pallet.blend --frames 50
```

---

## Project Structure

```
PalletDataGenerator/
├── src/palletdatagenerator/          # Main package
│   ├── __init__.py                   # Package exports
│   ├── cli.py                        # CLI entry point (palletgen command)
│   ├── generator.py                  # Main orchestrator
│   ├── config.py                     # Configuration dataclasses
│   ├── blender_runner.py             # Blender process management
│   ├── utils.py                      # Logging, validation, manifests
│   └── modes/                        # Generation mode implementations
│       ├── base_generator.py         # Abstract base (GPU, render, compositor)
│       ├── single_pallet.py          # Single pallet generation
│       ├── warehouse.py              # Warehouse scene generation
│       └── visibility_utils.py       # Face detection, ray casting
│
├── tests/                            # Pytest test suite
├── docs/                             # Sphinx documentation source
├── scenes/                           # Example Blender scenes
│   ├── one_pallet.blend              # Single pallet scene (recommended)
│   ├── warehouse_objects.blend       # Warehouse scene
│   ├── warehouse_objects_amr.blend   # Warehouse with AMR robot
│   └── assets/                       # Materials and 3D models
├── original_files/                   # Legacy reference implementations
├── scripts/                          # Dev setup scripts (bat, ps1, sh)
├── output/                           # Generated datasets (gitignored)
│
├── pyproject.toml                    # Python project metadata
├── requirements.txt                  # Core dependencies
├── requirements-dev.txt              # Development dependencies
├── requirements-optional.txt         # Optional packages (VOC support)
├── Dockerfile                        # Multi-stage Docker build
├── docker-compose.yml                # Docker compose configuration
├── .pre-commit-config.yaml           # Pre-commit hooks
├── CHANGELOG.md                      # Version history
├── CONTRIBUTING.md                   # Contributing guidelines
└── LICENSE                           # MIT license
```

---

## Dependencies

### Core

```
PyYAML >= 6.0              # Configuration parsing
Pillow >= 9.0.0            # Image processing
numpy >= 1.21.0            # Numerical operations
matplotlib >= 3.5.0        # 3D static visualization
plotly >= 5.0.0            # Interactive HTML 3D figures
```

### Blender-Provided (inside Blender Python)

```
bpy                        # Blender Python API
mathutils                  # Vectors, Matrices, Quaternions
bpy_extras                 # Camera projection utilities
```

### Optional

```
pascal-voc-writer >= 0.1.4 # PASCAL VOC XML export
lxml >= 4.9.0              # XML processing
```

### Development

```
pytest, pytest-cov, pytest-mock   # Testing
black, ruff, mypy                 # Code quality
sphinx, sphinx-rtd-theme          # Documentation
pre-commit, bandit                # Hooks, security
```

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository and create a feature branch
2. Make changes with proper tests
3. Run quality checks: `black`, `ruff`, `mypy`, `pytest`
4. Update documentation if needed
5. Submit a Pull Request with clear description

---

## License & Citation

### License

MIT License - see [LICENSE](LICENSE).

### Citation

```bibtex
@software{palletdatagenerator2025,
  title={PalletDataGenerator: Professional Synthetic Pallet Dataset Generation},
  author={Ibrahim Boubakri},
  year={2025},
  url={https://github.com/boubakriibrahim/PalletDataGenerator},
  version={0.1.3}
}
```

---

## Links

- [Documentation](https://boubakriibrahim.github.io/PalletDataGenerator) - Guides and API reference
- [Issue Tracker](https://github.com/boubakriibrahim/PalletDataGenerator/issues) - Report bugs
- [PyPI Package](https://pypi.org/project/palletdatagenerator/) - Latest releases
- [PalletDetection](https://github.com/boubakriibrahim/PalletDetection) - Companion ML training project
- [Blender](https://www.blender.org/) - 3D rendering engine

---

## Author

**Ibrahim Boubakri**
GitHub: [@boubakriibrahim](https://github.com/boubakriibrahim)
