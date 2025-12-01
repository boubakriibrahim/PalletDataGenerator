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

## [INFO] Overview

PalletDataGenerator is a comprehensive, production-ready solution for creating photorealistic synthetic datasets of pallets and warehouse environments. Designed with professional computer vision workflows in mind, it bridges the gap between research needs and industry-grade dataset generation.

### [INFO] Key Features

- [UNK] **Dual Generation Modes**: Single pallet focus and complex warehouse scenarios
- [INFO] **Multiple Export Formats**: YOLO, COCO JSON, and PASCAL VOC XML annotations
- [INFO] **Advanced Keypoints Generation**: Automatic face detection with 6 keypoints per face, visibility tracking, and 3D debug visualization
- [INFO] **3D Debug Visualization**: Interactive HTML figures and coordinate tracking for keypoints analysis
- [INFO] **GPU-Accelerated Rendering**: High-performance generation with Blender Cycles
- [UNK] **Flexible Configuration**: YAML configs with CLI parameter overrides
- [INFO] **Professional Output Structure**: Organized `generated_XXXX` batch folders with comprehensive metadata
- [UNK][UNK] **Modular Architecture**: Clean, extensible, and thoroughly tested codebase
- [INFO] **Photorealistic Results**: Advanced lighting, materials, and post-processing

## [INFO] Quick Start

### Prerequisites

- **Python 3.11+**
- **Blender 4.5+** (automatically detected or manually specified)
- **NVIDIA GPU** (recommended for optimal performance)

### Installation

```bash
# Install from PyPI (recommended)
pip install palletdatagenerator

# Or install from source for latest features
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator
pip install -e .
```

### Basic Usage

#### Generate Warehouse Dataset
```bash
# Generate 50 warehouse scene images with multiple pallets and boxes
palletgen -m warehouse scenes/warehouse_objects.blend

# Custom configuration
palletgen -m warehouse scenes/warehouse_objects.blend \
    --frames 100 \
    --resolution 1920 1080 \
    --output custom_output_dir
```

#### Generate Single Pallet Dataset
```bash
# Generate focused single pallet images
palletgen -m single_pallet scenes/one_pallet.blend

# High-resolution batch
palletgen -m single_pallet scenes/one_pallet.blend \
    --frames 200 \
    --resolution 2048 1536
```

## [UNK] Example Outputs

### Warehouse Mode
Generate complex warehouse scenes with multiple pallets, stacked boxes, and realistic lighting:

<div align="center">
<img src="readme_images/examples/warehouse_example_1.png" width="400" alt="Warehouse Example 1">
<img src="readme_images/examples/warehouse_example_2.png" width="400" alt="Warehouse Example 2">
</div>

### Single Pallet Mode
Generate focused single pallet scenes with detailed box arrangements:

<div align="center">
<img src="readme_images/examples/single_pallet_example_1.png" width="400" alt="Single Pallet Example 1">
<img src="readme_images/examples/single_pallet_example_2.png" width="400" alt="Single Pallet Example 2">
</div>

### Multi-Modal Outputs
Each frame generates comprehensive data for training:

| RGB Image | Analysis Overlay | Depth Map | Normal Map |
|-----------|------------------|-----------|------------|
| <img src="readme_images/outputs/single_pallet_example.png" width="200"> | <img src="readme_images/outputs/analysis_example.png" width="200"> | <img src="readme_images/outputs/depth_example.png" width="200"> | <img src="readme_images/outputs/normal_example.png" width="200"> |
| <img src="readme_images/outputs/warehouse_example.png" width="200"> | <img src="readme_images/outputs/analysis_example_2.png" width="200"> | <img src="readme_images/outputs/warehouse_depth_example.png" width="200"> | <img src="readme_images/outputs/warehouse_normal_example.png" width="200"> |

### [INFO] Keypoints Generation Examples
Advanced face detection and keypoints tracking with 3D visualization:

| Original Image | Keypoints Analysis | 3D Debug Visualization |
|----------------|-------------------|------------------------|
| <img src="readme_images/examples/single_pallet_keypoints_example.png" width="200"> | <img src="readme_images/outputs/keypoints_analysis_example.png" width="200"> | <img src="readme_images/outputs/debug_3d_example.png" width="200"> |

**Keypoints Features:**
- **Selective face detection**: 1-2 most visible faces per pallet (not all faces)
- **6 keypoints per selected face** with precise 2D/3D coordinates
- **Visibility tracking** using ray casting for occlusion detection
- **Interactive 3D HTML figures** for detailed analysis
- **Comprehensive debug information** including face selection criteria
- **YOLO format compatibility** for seamless integration with training pipelines

### [INFO] 3D Debug Visualization
Advanced debugging tools for keypoints analysis and face detection:

| Interactive 3D Figure | Debug Coordinates | 3D Visualization |
|----------------------|-------------------|------------------|
| [[INFO] Open Interactive 3D](readme_images/outputs/debug_3d_interactive_example.html) | [[INFO] View Coordinates](readme_images/outputs/debug_3d_coordinates_example.txt) | <img src="readme_images/outputs/debug_3d_example.png" width="200"> |

**Debug Features:**
- **Interactive 3D visualization** with Plotly.js for real-time exploration
- **Face selection analysis** showing which faces were chosen and why
- **Camera positioning** with distance calculations to each face
- **Pallet corner visualization** with camera-to-corner distance lines
- **Comprehensive coordinate tracking** for debugging and validation
- **Note:** Keypoints are only visible in 2D analysis images, not in 3D visualization

## [UNK][UNK] Architecture & Features

### Generation Modes

#### [UNK] **Warehouse Mode**
- **Multi-pallet scenes** with realistic warehouse layouts
- **Dynamic box stacking** with collection-aware placement
- **Procedural lighting** and environment variations
- **Complex occlusion scenarios** for robust model training

#### [INFO] **Single Pallet Mode**
- **Focused pallet detection** with controlled backgrounds
- **Precise annotation quality** for fine-grained training
- **Camera angle variations** including side and corner views
- **Configurable cropping and occlusion levels**

### [INFO] **Advanced Keypoints Generation**
- **Automatic face detection** by scanning for objects with "face" in their name
- **Selective face detection**: Detects 1-2 most visible faces from the pallet (not all faces)
- **6 keypoints per selected face**: 2 middle (top-down), 2 left (top-down), 2 right (top-down)
- **Visibility tracking** using ray casting to detect obstacles between face and camera
- **YOLO format output** with normalized coordinates and visibility flags
- **Analysis visualization** showing keypoints with different colors for visible/hidden states
- **3D coordinate tracking** with detailed debug information for each selected face
- **Interactive HTML figures** for 3D visualization and analysis
- **Comprehensive metadata** including face selection criteria and camera positioning

### Export Formats

#### [INFO] **YOLO Format**
```
# Example: 000000.txt
0 0.475345 0.595753 0.247050 0.102537
```

#### [INFO] **Keypoints Labels (YOLO Format)**
```
# Example: keypoints_labels/000000.txt
0 0.573150 0.639442 0.284453 0.139362 0.580366 0.603590 2 0.578420 0.669213 2 0.715376 0.569761 2 0.710409 0.633069 2 0.430924 0.641035 2 0.432683 0.709123 2
```
Format: `class_id x_center y_center width height kp1_x kp1_y kp1_v kp2_x kp2_y kp2_v ...`
- Visibility: `2`=visible, `0`=hidden
- 6 keypoints per face: middle (top/bottom), left (top/bottom), right (top/bottom)
- **Real example** from generated dataset with actual face detection results

#### [UNK] **COCO JSON**
```json
{
    "images": [{"id": 1, "file_name": "000000.png", "width": 1024, "height": 768}],
    "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [...]}],
    "categories": [{"id": 1, "name": "pallet", "supercategory": "object"}]
}
```

#### [INFO] **PASCAL VOC XML**
```xml
<annotation>
    <object>
        <name>pallet</name>
        <bndbox>
            <xmin>123</xmin><ymin>456</ymin>
            <xmax>789</xmax><ymax>654</ymax>
        </bndbox>
    </object>
</annotation>
```

### Output Structure

```
output/
[UNK][UNK][UNK] warehouse/
[UNK]   [UNK][UNK][UNK] generated_000001/
[UNK]   [UNK]   [UNK][UNK][UNK] images/          # RGB images (PNG)
[UNK]   [UNK]   [UNK][UNK][UNK] analysis/        # Overlay analysis images with keypoints
[UNK]   [UNK]   [UNK][UNK][UNK] depth/           # Depth maps (PNG)
[UNK]   [UNK]   [UNK][UNK][UNK] normals/         # Normal maps (PNG)
[UNK]   [UNK]   [UNK][UNK][UNK] index/           # Index/segmentation maps
[UNK]   [UNK]   [UNK][UNK][UNK] yolo_labels/     # YOLO format annotations
[UNK]   [UNK]   [UNK][UNK][UNK] keypoints_labels/ # Keypoints annotations (YOLO format)
[UNK]   [UNK]   [UNK][UNK][UNK] face_2d_boxes/   # 2D bounding boxes for detected faces
[UNK]   [UNK]   [UNK][UNK][UNK] face_3d_coordinates/ # 3D coordinates for keypoints
[UNK]   [UNK]   [UNK][UNK][UNK] debug_3d/        # 3D debug visualization
[UNK]   [UNK]   [UNK]   [UNK][UNK][UNK] coordinates/ # Detailed coordinate information
[UNK]   [UNK]   [UNK]   [UNK][UNK][UNK] figures/     # Interactive HTML 3D figures
[UNK]   [UNK]   [UNK]   [UNK][UNK][UNK] images/      # 3D debug visualization images
[UNK]   [UNK]   [UNK][UNK][UNK] voc_xml/         # PASCAL VOC annotations
[UNK]   [UNK]   [UNK][UNK][UNK] coco/            # COCO JSON annotations
[UNK]   [UNK][UNK][UNK] generated_000002/    # Next batch...
[UNK][UNK][UNK] single_pallet/
    [UNK][UNK][UNK] generated_000001/    # Same structure
```

### [INFO] Debug 3D Output Details

The `debug_3d/` folder contains comprehensive debugging information:

#### **Interactive HTML Figures** (`figures/`)
- **Real-time 3D visualization** using Plotly.js
- **Interactive controls**: rotate, zoom, pan, reset view
- **Face highlighting**: selected faces in red, unselected in blue
- **Keypoint visualization**: 6 keypoints per selected face
- **Camera position**: green diamond showing camera location
- **Distance calculations**: real-time distance from camera to each face

#### **Coordinate Files** (`coordinates/`)
Detailed text files containing:
```
Frame 0 - 3D Coordinates Debug
Object: pallet
Camera Position: (0.944, 2.536, 1.366)
Selected Faces: face_3, face_1

Pallet Corner Points (8 corners):
  Corner 0: (-0.384, -0.600, 0.020) - Distance: 3.663
  Corner 1: (-0.384, -0.600, 0.165) - Distance: 3.612
  ...

All Face Definitions (6 faces total):
  face_0 (corners [0, 1, 2, 3]):
    Center: (-0.384, 0.000, 0.093) - Distance: 3.134
    Status: not selected
  face_1 (corners [4, 5, 6, 7]):
    Center: (0.400, 0.000, 0.093) - Distance: 2.890
    Status: SELECTED
  ...

Selected Face Details:
  face_3 (index 3):
    Center Position: (0.008, 0.600, 0.093)
    Distance from Camera: 2.499
    2D Bounding Box: x_min=441.3, y_min=437.6, x_max=732.5, y_max=544.6
    3D Bounding Box: {...}
```

#### **Debug Images** (`images/`)
- **Static 3D visualization** for quick reference
- **Face selection visualization** showing which faces were chosen
- **Coordinate system reference** for debugging

### [UNK] Using Debug 3D Features

#### **Interactive HTML Visualization**
1. **Open the HTML file** in any modern web browser
2. **Navigate the 3D scene**:
   - **Rotate**: Click and drag to rotate the view
   - **Zoom**: Use mouse wheel to zoom in/out
   - **Pan**: Right-click and drag to pan the view
   - **Reset**: Double-click to reset to default view
3. **Analyze face selection**:
   - **Red circles**: Pallet corners (8 corners total)
   - **Blue diamond**: Camera position
   - **Gray dashed lines**: Camera-to-corner distance visualization
   - **Green/Orange faces**: Selected faces for keypoints generation (face_3, face_1)
   - **Note**: Keypoints are only visible in 2D analysis images, not in 3D visualization

#### **Coordinate Analysis**
The coordinate files provide detailed information for debugging:
- **Face selection criteria**: Why certain faces were chosen
- **Distance calculations**: Camera-to-face distances for selection
- **Bounding box data**: Both 2D and 3D bounding box information
- **Keypoint positions**: Exact 3D coordinates of all keypoints

#### **Example Usage**
```bash
# Generate dataset with debug 3D enabled
palletgen -m single_pallet scenes/one_pallet.blend --frames 10

# View debug files
ls output/single_pallet/generated_XXXXXX/debug_3d/
# coordinates/  figures/  images/

# Open interactive 3D visualization
open output/single_pallet/generated_XXXXXX/debug_3d/figures/frame_000000_3d_interactive.html

# View coordinate details
cat output/single_pallet/generated_XXXXXX/debug_3d/coordinates/frame_000000_coordinates.txt
```

## [INFO] Configuration

### CLI Parameters

```bash
palletgen --help

usage: palletgen [-h] [-m {single_pallet,warehouse}] [-f FRAMES]
                 [-r WIDTH HEIGHT] [-o OUTPUT] scene_path

Generate synthetic pallet datasets using Blender

positional arguments:
  scene_path            Path to Blender scene file (.blend)

optional arguments:
  -h, --help            show this help message and exit
  -m, --mode           Generation mode: single_pallet or warehouse (default: single_pallet)
  -f, --frames         Number of frames to generate (default: 50)
  -r, --resolution     Image resolution as WIDTH HEIGHT (default: 1024 768)
  -o, --output         Output directory (default: output/{mode}/generated_XXXXXX)
```

### Advanced Configuration

The system supports extensive customization through internal configuration:

```python
# Single Pallet Configuration
SINGLE_PALLET_CONFIG = {
    "num_images": 50,
    "resolution_x": 1024,
    "resolution_y": 768,
    "render_engine": "CYCLES",
    "camera_focal_mm": 35.0,
    "side_face_probability": 0.9,
    "allow_cropping": True,
    "min_visible_area_ratio": 0.3,
    "add_floor": True,
    "depth_scale": 1000.0,
    # Keypoints Generation Options
    "generate_keypoints": True,
    "keypoints_min_face_area": 80,
    "keypoints_visibility_check": False,
    "keypoints_show_3d_labels": False,
    "keypoints_show_2d_labels": False,
    "analysis_show_keypoints": True,
    "analysis_show_2d_boxes": True,
    "analysis_show_3d_coordinates": True,
    # ... many more options
}

# Warehouse Configuration
WAREHOUSE_CONFIG = {
    "num_images": 50,
    "resolution_x": 1024,
    "resolution_y": 768,
    "max_boxes_per_pallet": 8,
    "stacking_probability": 0.7,
    "lighting_variations": True,
    "camera_movement_range": 5.0,
    # Keypoints Generation Options (same as single pallet)
    "generate_keypoints": True,
    "keypoints_min_face_area": 80,
    "keypoints_visibility_check": False,
    "analysis_show_keypoints": True,
    "analysis_show_2d_boxes": True,
    "analysis_show_3d_coordinates": True,
    # ... extensive warehouse-specific options
}
```

## [UNK][UNK] Development Setup

### Development Installation

```bash
# Clone and setup development environment
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Install in development mode with all dependencies
pip install -e ".[dev,docs,test]"

# Install pre-commit hooks for code quality
pre-commit install
```

### Code Quality Tools

```bash
# Run code formatting
black src/ tests/

# Run linting
ruff check src/ tests/

# Run type checking
mypy src/

# Run all tests with coverage
pytest --cov=palletdatagenerator --cov-report=html
```

### Project Structure

```
PalletDataGenerator/
[UNK][UNK][UNK] src/palletdatagenerator/
[UNK]   [UNK][UNK][UNK] __init__.py
[UNK]   [UNK][UNK][UNK] cli.py                    # Command-line interface
[UNK]   [UNK][UNK][UNK] generator.py              # Main generator class
[UNK]   [UNK][UNK][UNK] config.py                 # Configuration management
[UNK]   [UNK][UNK][UNK] blender_runner.py         # Blender execution handler
[UNK]   [UNK][UNK][UNK] utils.py                  # Shared utilities
[UNK]   [UNK][UNK][UNK] modes/
[UNK]       [UNK][UNK][UNK] base_generator.py     # Abstract base class
[UNK]       [UNK][UNK][UNK] single_pallet.py      # Single pallet mode
[UNK]       [UNK][UNK][UNK] warehouse.py          # Warehouse mode
[UNK][UNK][UNK] tests/                        # Comprehensive test suite
[UNK][UNK][UNK] docs/                         # Sphinx documentation
[UNK][UNK][UNK] scenes/                       # Example Blender scenes
[UNK][UNK][UNK] original_files/               # Legacy reference implementations
[UNK][UNK][UNK] scripts/                      # Development scripts
[UNK][UNK][UNK] readme_images/               # README assets
```

## [UNK] API Reference

### Core Classes

#### `PalletDataGenerator`

Main generator class that orchestrates the entire generation process.

```python
from palletdatagenerator import PalletDataGenerator

generator = PalletDataGenerator(
    scene_path="scenes/warehouse_objects.blend",
    mode="warehouse",
    output_dir="custom_output"
)

# Generate dataset
generator.generate_dataset(num_frames=100)
```

#### Mode-Specific Generators

```python
from palletdatagenerator.modes import WarehouseMode, SinglePalletMode

# Warehouse mode with custom configuration
warehouse = WarehouseMode(config=custom_warehouse_config)
warehouse.generate_scene(frame_number=0)

# Single pallet mode
single = SinglePalletMode(config=custom_single_config)
single.generate_scene(frame_number=0)
```

### Utility Functions

```python
from palletdatagenerator.utils import (
    find_blender_executable,
    setup_logging,
    validate_scene_file
)

# Auto-detect Blender installation
blender_path = find_blender_executable()

# Validate scene compatibility
is_valid = validate_scene_file("path/to/scene.blend")
```

## [UNK] Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork the repository** and create a feature branch
2. **Make your changes** with proper testing
3. **Run quality checks**: `black`, `ruff`, `mypy`, `pytest`
4. **Update documentation** if needed
5. **Submit a Pull Request** with clear description

## [INFO] License & Citation

### License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### Citation

If you use PalletDataGenerator in your research, please cite:

```bibtex
@software{palletdatagenerator2025,
  title={PalletDataGenerator: Professional Synthetic Pallet Dataset Generation},
  author={Ibrahim Boubakri},
  year={2025},
  url={https://github.com/boubakriibrahim/PalletDataGenerator},
  version={0.1.3}
}
```

## [UNK] Links & Resources

- [UNK] **[Documentation](https://boubakriibrahim.github.io/PalletDataGenerator)** - Comprehensive guides and API reference
- [UNK] **[Issue Tracker](https://github.com/boubakriibrahim/PalletDataGenerator/issues)** - Report bugs and request features
- [INFO] **[Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)** - Community support and ideas
- [INFO] **[PyPI Package](https://pypi.org/project/palletdatagenerator/)** - Latest releases and installation
- [UNK] **[Blender](https://www.blender.org/)** - 3D rendering engine
- [UNK] **[Computer Vision Datasets](https://github.com/topics/computer-vision)** - Related projects

## [UNK] Acknowledgments

- **Blender Foundation** for the incredible open-source 3D suite
- **Computer Vision Community** for inspiration and feedback
- **Contributors** who help improve this project
- **Warehouse Industry Partners** for real-world validation

---

<div align="center">

**Made with [UNK][UNK] for the Computer Vision Community**

[INFO] **Star this repo** if you find it useful! [INFO]

</div>
