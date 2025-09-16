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

## 🎯 Overview

PalletDataGenerator is a comprehensive, production-ready solution for creating photorealistic synthetic datasets of pallets and warehouse environments. Designed with professional computer vision workflows in mind, it bridges the gap between research needs and industry-grade dataset generation.

### ✨ Key Features

- 🎬 **Dual Generation Modes**: Single pallet focus and complex warehouse scenarios
- 📊 **Multiple Export Formats**: YOLO, COCO JSON, and PASCAL VOC XML annotations
- ⚡ **GPU-Accelerated Rendering**: High-performance generation with Blender Cycles
- 🔧 **Flexible Configuration**: YAML configs with CLI parameter overrides
- 📦 **Professional Output Structure**: Organized `generated_XXXX` batch folders
- 🏗️ **Modular Architecture**: Clean, extensible, and thoroughly tested codebase
- 🌟 **Photorealistic Results**: Advanced lighting, materials, and post-processing

## 🚀 Quick Start

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

## 📸 Example Outputs

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

## 🏗️ Architecture & Features

### Generation Modes

#### 🏭 **Warehouse Mode**
- **Multi-pallet scenes** with realistic warehouse layouts
- **Dynamic box stacking** with collection-aware placement
- **Procedural lighting** and environment variations
- **Complex occlusion scenarios** for robust model training

#### 📦 **Single Pallet Mode**
- **Focused pallet detection** with controlled backgrounds
- **Precise annotation quality** for fine-grained training
- **Camera angle variations** including side and corner views
- **Configurable cropping and occlusion levels**

### Export Formats

#### 🎯 **YOLO Format**
```
# Example: 000000.txt
0 0.475345 0.595753 0.247050 0.102537
```

#### 📋 **COCO JSON**
```json
{
    "images": [{"id": 1, "file_name": "000000.png", "width": 1024, "height": 768}],
    "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [...]}],
    "categories": [{"id": 1, "name": "pallet", "supercategory": "object"}]
}
```

#### 📄 **PASCAL VOC XML**
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
├── warehouse/
│   ├── generated_000001/
│   │   ├── images/          # RGB images (PNG)
│   │   ├── analysis/        # Overlay analysis images
│   │   ├── depth/           # Depth maps (PNG)
│   │   ├── normals/         # Normal maps (PNG)
│   │   ├── index/           # Index/segmentation maps
│   │   ├── yolo_labels/     # YOLO format annotations
│   │   ├── voc_xml/         # PASCAL VOC annotations
│   │   └── coco/            # COCO JSON annotations
│   └── generated_000002/    # Next batch...
└── single_pallet/
    └── generated_000001/    # Same structure
```

## ⚙️ Configuration

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
    # ... extensive warehouse-specific options
}
```

## 🛠️ Development Setup

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
├── src/palletdatagenerator/
│   ├── __init__.py
│   ├── cli.py                    # Command-line interface
│   ├── generator.py              # Main generator class
│   ├── config.py                 # Configuration management
│   ├── blender_runner.py         # Blender execution handler
│   ├── utils.py                  # Shared utilities
│   └── modes/
│       ├── base_generator.py     # Abstract base class
│       ├── single_pallet.py      # Single pallet mode
│       └── warehouse.py          # Warehouse mode
├── tests/                        # Comprehensive test suite
├── docs/                         # Sphinx documentation
├── scenes/                       # Example Blender scenes
├── original_files/               # Legacy reference implementations
├── scripts/                      # Development scripts
└── readme_images/               # README assets
```

## 📚 API Reference

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

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork the repository** and create a feature branch
2. **Make your changes** with proper testing
3. **Run quality checks**: `black`, `ruff`, `mypy`, `pytest`
4. **Update documentation** if needed
5. **Submit a Pull Request** with clear description

## 📄 License & Citation

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
  version={0.1.2}
}
```

## 🔗 Links & Resources

- 📖 **[Documentation](https://boubakriibrahim.github.io/PalletDataGenerator)** - Comprehensive guides and API reference
- 🐛 **[Issue Tracker](https://github.com/boubakriibrahim/PalletDataGenerator/issues)** - Report bugs and request features
- 💬 **[Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)** - Community support and ideas
- 📦 **[PyPI Package](https://pypi.org/project/palletdatagenerator/)** - Latest releases and installation
- 🎬 **[Blender](https://www.blender.org/)** - 3D rendering engine
- 🤖 **[Computer Vision Datasets](https://github.com/topics/computer-vision)** - Related projects

## 🙏 Acknowledgments

- **Blender Foundation** for the incredible open-source 3D suite
- **Computer Vision Community** for inspiration and feedback
- **Contributors** who help improve this project
- **Warehouse Industry Partners** for real-world validation

---

<div align="center">

**Made with ❤️ for the Computer Vision Community**

⭐ **Star this repo** if you find it useful! ⭐

</div>
