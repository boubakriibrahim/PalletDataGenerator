# PalletDataGenerator Documentation

```{image} _static/logo.png
:alt: PalletDataGenerator Logo
:width: 200px
:align: center
```

**A professional Python library for generating synthetic pallet datasets using Blender for computer vision tasks.**

[![PyPI version](https://badge.fury.io/py/palletdatagenerator.svg)](https://badge.fury.io/py/palletdatagenerator)
[![Build Status](https://github.com/boubakriibrahim/PalletDataGenerator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/boubakriibrahim/PalletDataGenerator/actions/workflows/ci-cd.yml)
[![Coverage Status](https://coveralls.io/repos/github/boubakriibrahim/PalletDataGenerator/badge.svg?branch=main)](https://coveralls.io/github/boubakriibrahim/PalletDataGenerator?branch=main)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/palletdatagenerator.svg)](https://pypistats.org/packages/palletdatagenerator)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/palletdatagenerator.svg)](https://pypi.org/project/palletdatagenerator/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Blender 4.5+](https://img.shields.io/badge/blender-4.5+-orange.svg)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Documentation Status](https://readthedocs.org/projects/palletdatagenerator/badge/?version=latest)](https://palletdatagenerator.readthedocs.io/en/latest/?badge=latest)

## 🎯 Overview

PalletDataGenerator is a comprehensive solution for creating high-quality synthetic datasets of pallets and warehouse environments. Built with professional computer vision workflows in mind, it provides:

- **🎬 Realistic Scene Generation**: Single pallet and multi-pallet warehouse scenarios
- **📊 Multiple Export Formats**: YOLO, COCO, and PASCAL VOC annotations
- **⚡ GPU-Accelerated Rendering**: High-performance generation with Blender Cycles
- **🔧 Flexible Configuration**: YAML-based configuration with CLI overrides
- **📦 Batch Processing**: Organized output with `generated_XXXX` folder structure
- **🐍 Professional Architecture**: Clean, modular, and extensively tested

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

#### With Blender (Recommended)

```bash
# Open your Blender scene and run the generator
blender warehouse_objects.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset --num-frames 100
```

#### Direct Python Usage

```python
from palletdatagenerator import PalletDataGenerator
from palletdatagenerator.core.generator import GenerationConfig

# Create generator
generator = PalletDataGenerator()

# Configure generation
config = GenerationConfig(
    scene_type="warehouse",
    num_frames=100,
    resolution=(1280, 720),
    output_dir="./dataset",
    export_formats=["yolo", "coco"]
)

# Generate dataset
results = generator.generate_dataset(config)
```

## 📚 Documentation

```{toctree}
:maxdepth: 2
:caption: Contents:

installation
quickstart
configuration
api/index
examples/index
tutorials/index
development
changelog
```

## 🏗️ Architecture

```{mermaid}
graph TB
    A[Blender Scene] --> B[Scene Validator]
    B --> C[Generator Engine]
    C --> D[Randomizer]
    C --> E[Camera Controller]
    C --> F[Lighting Manager]
    D --> G[Renderer]
    E --> G
    F --> G
    G --> H[Image Output]
    G --> I[Annotation Extractor]
    I --> J[YOLO Exporter]
    I --> K[COCO Exporter]
    I --> L[VOC Exporter]
    H --> M[Dataset Output]
    J --> M
    K --> M
    L --> M
```

## 🎨 Features

### Core Capabilities

- **Scene Types**: Single pallet and warehouse environments
- **Export Formats**: YOLO, COCO, PASCAL VOC
- **Rendering**: GPU-accelerated with Blender Cycles
- **Randomization**: Materials, lighting, camera positions
- **Batch Processing**: Automated generation with organized output

### Advanced Features

- **Background Images**: Random background replacement from image folders
- **Forklift Simulation**: Realistic camera heights and movements (1.4-2.0m)
- **Analysis Images**: Debug visualization with annotation overlays
- **Depth Maps**: Optional depth information for 3D applications
- **Segmentation Masks**: Instance and semantic segmentation support

## 🔧 Configuration

### YAML Configuration

```yaml
generation:
  scene_type: "warehouse"
  num_frames: 500
  batch_size: 100
  num_batches: 5
  resolution: [1280, 720]
  export_formats: ["yolo", "coco", "voc"]

scene:
  backgrounds:
    use_random_backgrounds: true
    images_dir: "./backgrounds"
  camera:
    height_range: [1.4, 2.0]
    focal_length: 35.0

project:
  clone_to_desktop: false
  desktop_path: "auto"
```

### CLI Usage

```bash
# Generate with custom parameters
palletdatagenerator generate \
  --scene-type warehouse \
  --num-frames 500 \
  --num-batches 5 \
  --export-format yolo coco voc \
  --gpu \
  --verbose

# Use configuration file with overrides
palletdatagenerator generate \
  --config config.yaml \
  --output ./custom_output \
  --num-frames 1000
```

## 📋 Requirements

### System Requirements

- **Python**: 3.11 (3.11.13 recommended for optimal compatibility)
- **Blender**: 4.5+ (4.5.1 LTS recommended)
- **GPU**: NVIDIA (CUDA), AMD (OpenCL), or Apple Silicon (Metal) for acceleration
- **RAM**: 8GB minimum, 16GB+ recommended
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

- **Documentation**: [https://palletdatagenerator.readthedocs.io/](https://palletdatagenerator.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)

---

**Made with ❤️ for the Computer Vision Community**
