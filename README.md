# PalletDataGenerator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Professional Blender library for synthetic pallet and warehouse dataset generation with advanced rendering capabilities and comprehensive annotation support.**

## 🌟 Features

- **🎯 Multi-Generator Support**: Single pallet and complex warehouse scene generation
- **🎨 Advanced Rendering**: GPU-accelerated Cycles rendering with Filmic color management
- **📊 Multiple Export Formats**: YOLO, COCO, PASCAL VOC annotation formats
- **🔧 Professional Architecture**: Clean, modular, and extensible codebase
- **⚡ High Performance**: Optimized for batch processing and large dataset generation
- **🛡️ Robust Quality Assurance**: Comprehensive testing, linting, and type checking
- **📚 Complete Documentation**: Detailed API docs and usage examples
- **� Docker Support**: Containerized development and deployment
- **🚀 Multi-Platform**: Windows, macOS, Linux support with automated setup

## 🚀 Quick Start

### Option 1: Quick Installation (Recommended for Users)

```bash
# Install from PyPI (coming soon)
pip install palletdatagenerator

# Or install from source
pip install git+https://github.com/boubakriibrahim/PalletDataGenerator.git
```

### Option 2: Development Setup (Recommended for Contributors)

**Choose your platform:**

#### 🖥️ **Windows (Command Prompt/PowerShell)**
```cmd
# Clone repository
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Run setup script
scripts\setup-dev.bat
# or for PowerShell
powershell -ExecutionPolicy Bypass -File scripts\setup-dev.ps1
```

#### 🍎 **macOS / 🐧 Linux**
```bash
# Clone repository
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Run setup script
./scripts/setup-dev.sh
```

#### 🐳 **Docker (All Platforms)**
```bash
# Clone repository
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Start development environment
./scripts/docker-dev.sh dev

# Open shell in container
./scripts/docker-dev.sh shell
```

### Basic Usage

```python
import bpy
from palletdatagenerator import PalletGenerator, GenerationConfig

# Configure dataset generation
config = GenerationConfig(
    output_dir="outputs/my_dataset",
    num_images=100,
    resolution=(1280, 720),
    export_formats=["yolo", "coco"]
)

# Initialize generator
generator = PalletGenerator(config)

# Generate dataset
stats = generator.generate_dataset()
print(f"Generated {stats['images_generated']} images")
```

### Advanced Example

```python
from palletdatagenerator import WarehouseGenerator, GenerationConfig
from palletdatagenerator.utils import setup_logging

# Setup logging
setup_logging(level="INFO", log_file="generation.log")

# Advanced configuration
config = GenerationConfig(
    output_dir="outputs/warehouse_dataset",
    num_images=500,
    resolution=(1920, 1080),
    render_engine="CYCLES",
    camera_config={
        "focal_mm": 35.0,
        "height_range": (1.4, 2.0),
        "path_variation": 0.3
    },
    lighting_config={
        "randomize_per_frame": True,
        "light_count_range": (2, 4),
        "use_colored_lights": True,
        "colored_light_probability": 0.3
    },
    export_formats=["yolo", "coco", "voc"]
)

# Generate warehouse dataset
generator = WarehouseGenerator(config)

# Enable GPU rendering
gpu_backend = generator.enable_gpu()
print(f"Using GPU backend: {gpu_backend}")

# Generate dataset with progress tracking
stats = generator.generate_dataset()

# Print generation statistics
print("Generation Complete!")
print(f"Images: {stats['images_generated']}")
print(f"Pallets found: {stats['pallets_found']}")
print(f"Boxes found: {stats['boxes_found']}")
```

## 📁 Project Structure

```
PalletDataGenerator/
├── src/palletdatagenerator/
│   ├── __init__.py           # Main package interface
│   ├── core/                 # Core generation functionality
│   │   ├── generator.py      # Main generator classes
│   │   └── renderer.py       # Blender rendering interface
│   ├── exporters/            # Annotation exporters
│   │   ├── yolo.py          # YOLO format exporter
│   │   ├── coco.py          # COCO format exporter
│   │   └── voc.py           # PASCAL VOC exporter
│   └── utils.py             # Utility functions
├── tests/                   # Comprehensive test suite
├── docs/                    # Documentation
├── .github/workflows/       # CI/CD automation
└── configs/                 # Configuration examples
```

## 🎯 Use Cases

### Computer Vision Research
- **Object Detection**: Generate labeled datasets for pallet detection models
- **Pose Estimation**: Create datasets with precise 3D pose annotations
- **Segmentation**: Generate pixel-perfect segmentation masks
- **Domain Adaptation**: Bridge sim-to-real gap with photorealistic rendering

### Industrial Applications
- **Warehouse Automation**: Train robots for pallet handling and navigation
- **Quality Control**: Generate datasets for automated inspection systems
- **Logistics Optimization**: Create data for warehouse layout optimization
- **Safety Systems**: Train models for accident prevention in warehouses

### Academic Research
- **Synthetic Data Studies**: Investigate effectiveness of synthetic vs real data
- **Benchmark Creation**: Generate standardized evaluation datasets
- **Algorithm Development**: Rapid prototyping with unlimited labeled data

## 🔧 Configuration

### Generation Config

```python
config = GenerationConfig(
    # Basic settings
    output_dir="outputs/dataset",
    num_images=100,
    resolution=(1280, 720),
    render_engine="CYCLES",

    # Camera settings
    camera_config={
        "focal_mm": 35.0,        # Focal length
        "sensor_mm": 36.0,       # Sensor size
        "height_range": (1.0, 3.0),  # Camera height range
    },

    # Lighting settings
    lighting_config={
        "randomize_per_frame": True,
        "light_count_range": (2, 4),
        "use_colored_lights": True,
        "colored_light_probability": 0.6,
    },

    # Export formats
    export_formats=["yolo", "coco", "voc"]
)
```

### YAML Configuration

```yaml
# config.yaml
output_dir: "outputs/my_dataset"
num_images: 200
resolution: [1920, 1080]
render_engine: "CYCLES"

camera_config:
  focal_mm: 50.0
  height_range: [1.2, 2.5]

lighting_config:
  randomize_per_frame: true
  light_count_range: [3, 6]
  use_colored_lights: true

export_formats:
  - "yolo"
  - "coco"
```

## 📊 Output Formats

### Directory Structure
```
outputs/
└── my_dataset/
    ├── images/              # RGB images
    ├── depth/               # Depth maps (16-bit PNG)
    ├── normals/             # Surface normal maps
    ├── index/               # Object index maps
    ├── yolo_labels/         # YOLO format annotations
    ├── voc_xml/            # PASCAL VOC XML files
    ├── annotations.json     # COCO format annotations
    └── dataset_manifest.json # Complete dataset metadata
```

### YOLO Format
```
# frame_000001.txt
0 0.5123 0.3456 0.2345 0.1678  # class_id center_x center_y width height
1 0.7234 0.6789 0.1234 0.0987
```

### COCO Format
```json
{
  "images": [{"id": 1, "file_name": "frame_000001.png", "width": 1280, "height": 720}],
  "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [100, 200, 150, 120]}],
  "categories": [{"id": 1, "name": "pallet", "supercategory": "logistics"}]
}
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=palletdatagenerator --cov-report=html

# Run specific test categories
pytest -m "not slow"          # Skip slow tests
pytest -m "unit"              # Only unit tests
pytest -m "integration"       # Only integration tests
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

### Building Documentation

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build and serve docs locally
cd docs && make html && open _build/html/index.html

# Build for deployment
cd docs && make html
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes with proper tests and documentation
4. **Run** quality checks (`pre-commit run --all-files`)
5. **Commit** your changes (`git commit -m 'Add amazing feature'`)
6. **Push** to your branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

### Code Standards

- **Black** for code formatting
- **Ruff** for linting
- **MyPy** for type checking
- **Pytest** for testing (>90% coverage required)
- **Conventional Commits** for commit messages

### Command Line Interface

Once installed, you can use the CLI:

```bash
# Get version info
palletgen info --version

# Create config file
palletgen config create --output configs/my_config.yaml

# Generate dataset
palletgen generate --config configs/my_config.yaml --output datasets/my_dataset

# Validate config
palletgen config validate --config configs/my_config.yaml
```

### Available Aliases (After Development Setup)

The setup scripts create convenient aliases:

```bash
pgen info --version          # Short version of palletgen
pgen-test                   # Run all tests
pgen-lint                   # Run code quality checks
pgen-docs                   # Build documentation
pgen-format                 # Format code with Black and Ruff
pgen-clean                  # Clean Python cache files
```

## 🐳 Docker Usage

### Development with Docker

```bash
# Build and start development environment
./scripts/docker-dev.sh dev

# Open shell in development container
./scripts/docker-dev.sh shell

# Run tests in container
./scripts/docker-dev.sh test

# Build and serve documentation
./scripts/docker-dev.sh docs  # Available at http://localhost:8080

# Start Blender development environment (with GUI support)
./scripts/docker-dev.sh blender
```

### Docker Compose Services

| Service | Purpose | Ports |
|---------|---------|-------|
| `pallet-dev` | Development environment | 8000, 8888 |
| `pallet-prod` | Production container | - |
| `pallet-blender` | Blender development | 8000 |
| `pallet-test` | Testing and CI/CD | - |
| `pallet-docs` | Documentation server | 8080 |

### Production Deployment

```bash
# Build production image
docker build --target production -t palletgenerator:latest .

# Run production container
docker run -v $(pwd)/output:/home/pallet/app/output \
           -v $(pwd)/configs:/home/pallet/app/configs \
           palletgenerator:latest generate --config configs/production.yaml
```

## 🛠️ Development

### Development Setup (Automatic)

The setup scripts handle everything automatically:
- Python environment (conda or venv)
- Dependencies installation
- Pre-commit hooks
- Shell aliases
- Development tools

**After running setup scripts:**
```bash
# Activate environment (if using conda)
conda activate blender

# Or activate venv (if using venv)
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Start developing!
pgen-test    # Run tests
pgen-lint    # Check code quality
```

### Manual Development Setup

If you prefer manual setup:

```bash
# Create environment
conda create -n blender python=3.11 -y
conda activate blender

# Install dependencies
pip install -r requirements-dev.txt

# Install package in development mode
pip install -e .

# Setup pre-commit
pre-commit install

# Run tests
pytest tests/ -v
```

### Project Structure

```
PalletDataGenerator/
├── src/palletdatagenerator/   # Main package
│   ├── core/                     # Core generation logic
│   ├── exporters/                # Format exporters (YOLO, COCO, VOC)
│   ├── cli.py                    # Command-line interface
│   └── utils.py                  # Utilities
├── tests/                        # Test suite
├── docs/                         # Documentation
├── configs/                      # Configuration templates
├── scripts/                      # Development and deployment scripts
├── requirements*.txt             # Dependencies
├── Dockerfile                    # Docker configuration
├── docker-compose.yml           # Docker services
└── pyproject.toml               # Project configuration
```

### Code Quality

This project maintains high code quality standards:

- **Black** for code formatting
- **Ruff** for linting and code quality
- **Pre-commit hooks** for automated checks
- **Pytest** for comprehensive testing
- **Type hints** throughout codebase
- **Documentation** for all public APIs

```bash
# Run all quality checks
pgen-lint

# Format code
pgen-format

# Run tests with coverage
pgen-test
```

## 📈 Performance

### Optimization Tips

- **Use GPU rendering** for 5-10x speedup
- **Enable persistent data** for batch rendering
- **Adjust sample count** based on quality needs
- **Use adaptive sampling** for automatic optimization

## 🛠️ Requirements

### System Requirements
- **Python**: 3.11+ (3.11 recommended)
- **Blender**: 4.5+ (4.5 recommended)
- **Memory**: 8GB RAM minimum, 16GB+ recommended
- **Storage**: SSD recommended for large datasets

### GPU Support
- **NVIDIA**: CUDA/OptiX (RTX series recommended)
- **AMD**: HIP/OpenCL
- **Apple**: Metal (M series)
- **Intel**: OneAPI (Arc series)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Blender Foundation** for the amazing 3D creation suite
- **Computer Vision Community** for inspiration and best practices
- **Open Source Contributors** who make projects like this possible

## 📞 Support

- **📖 Documentation**: [https://boubakriibrahim.github.io/PalletDataGenerator/](https://boubakriibrahim.github.io/PalletDataGenerator/)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)
- **📧 Email**: [ibrahim@example.com](mailto:ibrahim@example.com)

---

<div align="center">

**[⭐ Star this project](https://github.com/boubakriibrahim/PalletDataGenerator) if you find it useful!**

Made with ❤️ by [Ibrahim Boubakri](https://github.com/boubakriibrahim)

</div>
