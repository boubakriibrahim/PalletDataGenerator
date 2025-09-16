# PalletDataGenerator Documentation

**A professional Python library for generating high-quality synthetic pallet datasets using Blender for computer vision and machine learning applications.**

[![PyPI version](https://badge.fury.io/py/palletdatagenerator.svg)](https://badge.fury.io/py/palletdatagenerator)
[![Build Status](https://github.com/boubakriibrahim/PalletDataGenerator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/boubakriibrahim/PalletDataGenerator/actions)
[![Coverage Status](https://coveralls.io/repos/github/boubakriibrahim/PalletDataGenerator/badge.svg?branch=main)](https://coveralls.io/github/boubakriibrahim/PalletDataGenerator?branch=main)
[![Documentation Status](https://boubakriibrahim.github.io/PalletDataGenerator/badge.svg)](https://boubakriibrahim.github.io/PalletDataGenerator)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/palletdatagenerator.svg)](https://pypistats.org/packages/palletdatagenerator)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.5+](https://img.shields.io/badge/blender-4.5+-orange.svg)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

```{admonition} Version 0.1.2 Release 🎉
:class: tip

This documentation covers **PalletDataGenerator v0.1.2**, featuring a completely redesigned unified architecture, embedded configuration system, and enhanced batch processing capabilities.

[See the full changelog →](https://github.com/boubakriibrahim/PalletDataGenerator/blob/main/CHANGELOG.md)
```

## 🎯 Overview

PalletDataGenerator is a comprehensive, production-ready solution for creating photorealistic synthetic datasets of pallets and warehouse environments. Designed with professional computer vision workflows in mind, it bridges the gap between research needs and industry-grade dataset generation.

### ✨ Key Features

- 🎬 **Dual Generation Modes**: Single pallet focus and complex warehouse scenarios
- 📊 **Multiple Export Formats**: YOLO, COCO JSON, and PASCAL VOC XML annotations
- ⚡ **GPU-Accelerated Rendering**: High-performance generation with Blender Cycles
- 🔧 **Unified Architecture**: Single `PalletDataGenerator` class with embedded configuration
- 📦 **Auto-Batch Management**: Organized `generated_XXXX` batch folders with sequencing
- 🏗️ **Modular Design**: Clean, extensible, and thoroughly tested codebase
- 🌟 **Photorealistic Results**: Advanced lighting, materials, and post-processing
- 🐳 **Docker Ready**: Complete containerization for deployment

## 🚀 Quick Start

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

#### Using Python API (New in v0.1.2)
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

## 📚 Documentation

```{toctree}
:maxdepth: 2
:caption: User Guide

installation
quickstart
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

## 🏗️ Architecture Overview

PalletDataGenerator v0.1.2 introduces a unified architecture:

```
┌─────────────────────────────────────┐
│         PalletDataGenerator         │
│  ┌──────────────┐ ┌────────────────┐│
│  │ DefaultConfig│ │  Mode System   ││
│  │   System     │ │ ┌─────────────┐││
│  └──────────────┘ │ │SinglePallet │││
│         │         │ └─────────────┘││
│         │         │ ┌─────────────┐││
│         └─────────┤ │ Warehouse   │││
│                   │ └─────────────┘││
│                   └────────────────┘│
│ ┌─────────────────────────────────┐ │
│ │      Blender Integration        │ │
│ │ ┌─────────┐ ┌─────────────────┐ │ │
│ │ │  Scene  │ │    Renderer     │ │ │
│ │ │Validator│ │                 │ │ │
│ │ └─────────┘ └─────────────────┘ │ │
│ └─────────────────────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │      Export System              │ │
│ │ ┌───────┐┌───────┐┌───────────┐ │ │
│ │ │ YOLO  ││ COCO  ││   VOC     │ │ │
│ │ └───────┘└───────┘└───────────┘ │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## 🚀 Key Features v0.1.2

### 🔄 Unified Generator
- Single entry point for all generation modes
- Embedded configuration with sensible defaults
- Automatic batch folder management

### 📁 Auto-Batch Management
```
output/
├── single_pallet/
│   ├── generated_000001/
│   ├── generated_000002/
│   └── generated_000003/
└── warehouse/
    ├── generated_000001/
    └── generated_000002/
```

### 🎯 Export Formats
- **YOLO**: `.txt` files with normalized bounding boxes
- **COCO**: `.json` with comprehensive metadata
- **PASCAL VOC**: `.xml` files for compatibility

### 🖼️ Multi-Modal Outputs
Each generated frame includes:
- RGB images (`images/`)
- Analysis overlays (`analysis/`)
- Depth maps (`depth/`)
- Normal maps (`normals/`)
- Index maps (`index/`)

## 💡 Quick Examples

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

## 📖 Learning Resources

- **🚀 [Quick Start Guide](quickstart.md)**: Get up and running in minutes
- **📋 [Installation Guide](installation.md)**: Detailed setup instructions
- **🔧 [API Reference](api/palletdatagenerator.html)**: Complete API documentation
- **📝 [Changelog](https://github.com/boubakriibrahim/PalletDataGenerator/blob/main/CHANGELOG.md)**: Version history and migration guides

## 🤝 Community & Support

- 🐛 **[Report Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)**
- 💬 **[Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)**
- 📧 **Email**: ibrahimbouakri1@gmail.com

---

```{admonition} 🎉 What's New in v0.1.2
:class: note

- **Unified API**: Single `PalletDataGenerator` class replaces separate mode classes
- **Embedded Config**: No more external YAML files required
- **Auto-Batching**: Automatic `generated_XXXXXX` folder creation
- **Better Error Handling**: Comprehensive validation and error reporting
- **Type Safety**: Full type annotations throughout
- **Docker Ready**: Production deployment support

[View Full Changelog →](https://github.com/boubakriibrahim/PalletDataGenerator/blob/main/CHANGELOG.md#020---2025-09-15)
```
- **Storage**: 1GB+ free space per 1000 generated images

## 🤝 Contributing

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

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Blender Foundation** for the amazing Blender software
- **Computer Vision Community** for dataset format standards
- **Contributors** who help improve this library

## 📞 Support

- **Documentation**: [https://boubakriibrahim.github.io/PalletDataGenerator](https://boubakriibrahim.github.io/PalletDataGenerator)
- **Issues**: [GitHub Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)

---

**Made with ❤️ for the Computer Vision Community**
