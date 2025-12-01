# PalletDataGenerator Documentation

**A professional Python library for generating high-quality synthetic pallet datasets using Blender for computer vision and machine learning applications.**

[![PyPI version](https://badge.fury.io/py/palletdatagenerator.svg)](https://badge.fury.io/py/palletdatagenerator)
[![Build Status](https://github.com/boubakriibrahim/PalletDataGenerator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/boubakriibrahim/PalletDataGenerator/actions)
[![Coverage Status](https://coveralls.io/repos/github/boubakriibrahim/PalletDataGenerator/badge.svg?branch=main)](https://coveralls.io/github/boubakriibrahim/PalletDataGenerator?branch=main)
[![Documentation Status](https://img.shields.io/badge/docs-GitHub%20Pages-blue?logo=github)](https://boubakriibrahim.github.io/PalletDataGenerator)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/palletdatagenerator.svg)](https://pypistats.org/packages/palletdatagenerator)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.5+](https://img.shields.io/badge/blender-4.5+-orange.svg)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

```{admonition} Version 0.1.3 Release [UNK]
:class: tip

This documentation covers **PalletDataGenerator v0.1.3**, featuring a completely redesigned unified architecture, embedded configuration system, and enhanced batch processing capabilities.

[See the full changelog [UNK]](https://github.com/boubakriibrahim/PalletDataGenerator/blob/main/CHANGELOG.md)
```

## [INFO] Overview

PalletDataGenerator is a comprehensive, production-ready solution for creating photorealistic synthetic datasets of pallets and warehouse environments. Designed with professional computer vision workflows in mind, it bridges the gap between research needs and industry-grade dataset generation.

### [INFO] Key Features

- [UNK] **Dual Generation Modes**: Single pallet focus and complex warehouse scenarios
- [INFO] **Multiple Export Formats**: YOLO, COCO JSON, and PASCAL VOC XML annotations
- [INFO] **Advanced Keypoints Generation**: Automatic face detection with 6 keypoints per face, visibility tracking, and 3D debug visualization
- [INFO] **3D Debug Visualization**: Interactive HTML figures and coordinate tracking for keypoints analysis
- [INFO] **GPU-Accelerated Rendering**: High-performance generation with Blender Cycles
- [UNK] **Unified Architecture**: Single `PalletDataGenerator` class with embedded configuration
- [INFO] **Auto-Batch Management**: Organized `generated_XXXX` batch folders with sequencing
- [UNK][UNK] **Modular Design**: Clean, extensible, and thoroughly tested codebase
- [INFO] **Photorealistic Results**: Advanced lighting, materials, and post-processing
- [UNK] **Docker Ready**: Complete containerization for deployment

## [INFO] Quick Start

### Installation

```bash
# Install the package
pip install palletdatagenerator

# Or install from source
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator
pip install -e .
```

### Basic Usage

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

#### Using Python API
```python
from palletdatagenerator import PalletDataGenerator

# Create generator instance
generator = PalletDataGenerator(
    scene_path="scenes/warehouse_objects.blend",
    mode="warehouse",
    output_dir="output"
)

# Generate dataset
generator.generate_dataset(num_frames=50)
```

## [UNK] Documentation

```{toctree}
:maxdepth: 2
:caption: User Guide

installation
quickstart
keypoints_generation
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/modules
```

```{toctree}
:maxdepth: 1
:caption: Development
```

## [UNK][UNK] Architecture Overview

```
[UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK]         PalletDataGenerator         [UNK]
[UNK]  [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK]  [UNK] DefaultConfig[UNK] [UNK]  Mode System   [UNK][UNK]
[UNK]  [UNK]   System     [UNK] [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK]  [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK] [UNK]SinglePallet [UNK][UNK][UNK]
[UNK]         [UNK]         [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK]         [UNK]         [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK]         [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK] Warehouse   [UNK][UNK][UNK]
[UNK]                   [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK]                   [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
[UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK]
[UNK] [UNK]      Blender Integration        [UNK] [UNK]
[UNK] [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK] [UNK]
[UNK] [UNK] [UNK]  Scene  [UNK] [UNK]    Renderer     [UNK] [UNK] [UNK]
[UNK] [UNK] [UNK]Validator[UNK] [UNK]                 [UNK] [UNK] [UNK]
[UNK] [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK] [UNK]
[UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK]
[UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK]
[UNK] [UNK]      Export System              [UNK] [UNK]
[UNK] [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK] [UNK]
[UNK] [UNK] [UNK] YOLO  [UNK][UNK] COCO  [UNK][UNK]   VOC     [UNK] [UNK] [UNK]
[UNK] [UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK] [UNK]
[UNK] [UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK] [UNK]
[UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK][UNK]
```

## [INFO] Key Features v0.1.3

### [INFO] Advanced Keypoints Generation
- **Selective face detection**: Detects 1-2 most visible faces from the pallet (not all faces)
- **6 keypoints per selected face**: 2 middle (top-down), 2 left (top-down), 2 right (top-down)
- **Visibility tracking**: Ray casting for occlusion detection between face and camera
- **YOLO format output**: Normalized coordinates with visibility flags (2=visible, 0=hidden)
- **Analysis visualization**: Keypoints with different colors for visible/hidden states

### [INFO] 3D Debug Visualization
- **Interactive HTML figures**: Real-time 3D visualization using Plotly.js
- **Face selection analysis**: Shows which faces were chosen and why
- **Camera positioning**: Distance calculations to each face with visual lines
- **Coordinate tracking**: Detailed 3D coordinate information for debugging
- **Debug output structure**: `debug_3d/` folder with coordinates, figures, and images

### [INFO] Enhanced Output Structure
- **keypoints_labels/**: YOLO format keypoints annotations
- **face_2d_boxes/**: 2D bounding boxes for detected faces
- **face_3d_coordinates/**: 3D coordinates for keypoints
- **debug_3d/coordinates/**: Detailed coordinate information
- **debug_3d/figures/**: Interactive HTML 3D figures
- **debug_3d/images/**: 3D debug visualization images

## [INFO] Key Features v0.1.2

### [UNK] Unified Generator
- Single entry point for all generation modes
- Embedded configuration with sensible defaults
- Automatic batch folder management

### [INFO] Auto-Batch Management
```
output/
[UNK][UNK][UNK] single_pallet/
[UNK]   [UNK][UNK][UNK] generated_000001/
[UNK]   [UNK][UNK][UNK] generated_000002/
[UNK]   [UNK][UNK][UNK] generated_000003/
[UNK][UNK][UNK] warehouse/
    [UNK][UNK][UNK] generated_000001/
    [UNK][UNK][UNK] generated_000002/
```

### [INFO] Export Formats
- **YOLO**: `.txt` files with normalized bounding boxes and keypoints
- **COCO**: `.json` with comprehensive metadata
- **PASCAL VOC**: `.xml` files for compatibility

### [UNK][UNK] Multi-Modal Outputs
Each generated frame includes:
- RGB images (`images/`)
- Analysis overlays (`analysis/`) with keypoints visualization
- Depth maps (`depth/`)
- Normal maps (`normals/`)
- Index maps (`index/`)
- Keypoints labels (`keypoints_labels/`) in YOLO format
- 3D debug visualization (`debug_3d/`) with interactive HTML figures
- Face coordinate tracking (`face_2d_boxes/`, `face_3d_coordinates/`)

## [INFO] Quick Examples

### Generate 100 Warehouse Images
```bash
palletgen -m warehouse scenes/warehouse_objects.blend -f 100
```

### High-Resolution Single Pallet Dataset
```bash
palletgen -m single_pallet scenes/one_pallet.blend \
    --frames 200 \
    --resolution 2048 1536
```

### Python API Usage
```python
from palletdatagenerator import PalletDataGenerator

generator = PalletDataGenerator(
    scene_path="scenes/warehouse_objects.blend",
    mode="warehouse",
    output_dir="my_dataset"
)

# Generate with custom settings
generator.generate_dataset(
    num_frames=100,
    resolution=(1920, 1080)
)
```

## [UNK] Learning Resources

- **[INFO] [Quick Start Guide](quickstart.md)**: Get up and running in minutes
- **[UNK] [Installation Guide](installation.md)**: Detailed setup instructions
- **[INFO] [Keypoints Generation Guide](keypoints_generation.md)**: Advanced face detection and keypoints tracking
- **[UNK] [API Reference](api/palletdatagenerator.html)**: Complete API documentation
- **[INFO] [Changelog](https://github.com/boubakriibrahim/PalletDataGenerator/blob/main/CHANGELOG.md)**: Version history and migration guides

## [UNK] Community & Support

- [UNK] **[Report Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)**
- [INFO] **[Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)**
- [UNK] **Email**: ibrahimbouakri1@gmail.com

---

```{admonition} [UNK] What's New in v0.1.3
:class: note

- **[INFO] Advanced Keypoints Generation**: Automatic face detection with 6 keypoints per selected face
  - Selective face detection (1-2 most visible faces, not all faces)
  - Visibility tracking with ray casting for occlusion detection
  - YOLO format output with visibility flags
- **[INFO] 3D Debug Visualization**: Interactive HTML figures and coordinate tracking
  - Real-time 3D visualization using Plotly.js
  - Face selection analysis and camera positioning
  - Comprehensive debug output structure
- **[INFO] Enhanced Output Structure**: New directories for comprehensive debugging
  - `keypoints_labels/`, `face_2d_boxes/`, `face_3d_coordinates/`
  - `debug_3d/` with coordinates, figures, and images
- **[UNK] Improved Documentation**: Updated guides and examples with real data
```

[View Full Changelog [UNK]](https://github.com/boubakriibrahim/PalletDataGenerator/blob/main/CHANGELOG.md#013---2025-01-15)
```
- **Storage**: 1GB+ free space per 1000 generated images

## [UNK] Contributing

We welcome contributions! Please see our [Contributing Guide](development.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Set up development environment
python -m palletdatagenerator setup --python-version 3.11

# Activate virtual environment
source pallet_env/bin/activate  # Linux/Mac
# or
pallet_env\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## [INFO] License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## [UNK] Acknowledgments

- **Blender Foundation** for the amazing Blender software
- **Computer Vision Community** for dataset format standards
- **Contributors** who help improve this library

## [UNK] Support

- **Documentation**: [https://boubakriibrahim.github.io/PalletDataGenerator](https://boubakriibrahim.github.io/PalletDataGenerator)
- **Issues**: [GitHub Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)

---

**Made with [UNK][UNK] for the Computer Vision Community**
