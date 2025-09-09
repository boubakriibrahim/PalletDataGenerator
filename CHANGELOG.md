# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/0.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial library structure and core functionality
- Support for single pallet and warehouse scene generation
- Multiple annotation format exporters (YOLO, COCO, PASCAL VOC)
- GPU-accelerated rendering support
- Comprehensive test suite with >90% coverage
- CLI interface for command-line usage
- Configuration file support (YAML)
- Automated CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality
- Professional documentation and examples

### Features
- **Core Generation Engine**: Modular generator system supporting different scene types
- **Multi-format Export**: Support for YOLO, COCO, and PASCAL VOC annotation formats
- **Flexible Configuration**: YAML-based configuration with command-line overrides
- **Quality Assurance**: Automated testing, linting, and formatting
- **Easy Installation**: Available on PyPI with simple pip installation
- **Professional Documentation**: Comprehensive docs with examples and API reference

## [0.1.0] - 2024-01-15

### Added
- Initial release of Pallet Data Generator
- Core library functionality for synthetic dataset generation
- Blender integration for 3D scene rendering
- Support for pallet and warehouse scene generation
- Multiple annotation format exports
- Professional development workflow
- Automated testing and CI/CD pipeline
- Documentation and examples

### Core Components
- `PalletDataGenerator`: Main library interface
- `BaseGenerator`: Abstract generator base class
- `PalletGenerator`: Single pallet scene generator
- `WarehouseGenerator`: Multi-pallet warehouse generator
- `BlenderRenderer`: Rendering engine interface
- `YOLOExporter`: YOLO format annotation exporter
- `COCOExporter`: COCO format annotation exporter
- `VOCExporter`: PASCAL VOC format annotation exporter

### Development Features
- Black code formatting
- Ruff linting with comprehensive rules
- MyPy static type checking
- Bandit security scanning
- Pre-commit hooks
- Pytest testing framework with fixtures
- GitHub Actions CI/CD
- Automated PyPI publishing
- Documentation generation with Sphinx

### Documentation
- Comprehensive README with installation and usage
- API documentation with examples
- Contributing guidelines
- Development setup instructions
- Configuration reference
- Example configurations and scripts

---

## Release Notes

### Version 0.1.0 - Initial Release

This is the first stable release of the Pallet Data Generator library. The library provides a professional, modular approach to generating synthetic datasets for computer vision tasks involving pallets and warehouse environments.

**Key Highlights:**
- 🎯 **Professional Architecture**: Clean, modular design following Python best practices
- 🔧 **Easy to Use**: Simple API with sensible defaults and comprehensive configuration options
- 📊 **Multiple Formats**: Support for YOLO, COCO, and PASCAL VOC annotation formats
- 🚀 **High Performance**: GPU-accelerated rendering with Blender integration
- 🧪 **Well Tested**: Comprehensive test suite with >90% code coverage
- 📚 **Great Documentation**: Clear documentation with examples and API reference
- 🔄 **CI/CD Ready**: Automated testing, building, and deployment pipeline

**What's Included:**
- Core library with generator classes
- Blender integration for 3D rendering
- Multiple annotation format exporters
- Command-line interface
- Configuration file support
- Comprehensive test suite
- Professional documentation
- Development tools and workflows

**Getting Started:**
```bash
pip install palletdatagenerator
```

```python
from palletdatagenerator import PalletDataGenerator
from palletdatagenerator.core.generator import GenerationConfig

# Create generator
generator = PalletDataGenerator()

# Configure generation
config = GenerationConfig(
    scene_type="single_pallet",
    num_frames=100,
    resolution=(640, 480),
    output_dir="./dataset",
    export_formats=["yolo", "coco"]
)

# Generate dataset
results = generator.generate_dataset(config)
```

For more information, see the [documentation](README.md) and [examples](examples/).

---

## Future Roadmap

### Planned Features
- Advanced scene randomization options
- Support for additional object types
- Integration with popular ML frameworks
- Real-time preview capabilities
- Cloud rendering support
- Advanced material and lighting systems

### Community
We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to the project.

---

*For the complete list of changes, see the [commit history](https://github.com/boubakriibrahim/PalletDataGenerator/commits/main).*
