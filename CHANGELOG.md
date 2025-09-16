# Changelog

All notable changes to this project will be documented in this file.

## [0.1.2] - 2025-09-15

### Added
- **Unit Test Suite**: Comprehensive test coverage for core functionality
- **Improved Documentation**: Updated documentation with current version and comprehensive changelog
- **Code Quality**: Enhanced pre-commit hooks and code quality tools
- **Version Consistency**: Aligned version numbers across all files

### Changed
- **Documentation Updates**: Refreshed README, docs structure, and API documentation
- **Pre-commit Configuration**: Updated hooks to handle acceptable security warnings
- **Error Handling**: Improved error messages and exception handling

### Fixed
- **Version Mismatch**: Synchronized version numbers across package files
- **Documentation Generation**: Fixed Sphinx configuration for proper version detection
- **Code Style**: Applied consistent formatting and fixed linting issues

## [0.1.1] - 2025-09-15

### Added
- **Unified Generator Architecture**: Complete refactor with a single `PalletDataGenerator` class
- **Embedded Configuration System**: Built-in configuration management with `DefaultConfig`
- **Auto-batch Management**: Automatic creation of `generated_XXXXXX` folders with proper sequencing
- **Comprehensive Error Handling**: Robust error reporting and recovery mechanisms
- **Professional Logging**: Structured logging with different verbosity levels
- **Type Annotations**: Full type hints throughout the codebase for better IDE support
- **Modular Mode System**: Clean separation between single pallet and warehouse generation modes
- **Enhanced CLI Interface**: Improved command-line interface with better help and validation
- **Docker Support**: Complete Docker containerization for easy deployment
- **Development Tools**: Pre-commit hooks, code formatting, and quality checks

### Changed
- **BREAKING**: Simplified API from separate mode classes to unified generator
- **BREAKING**: Changed default output structure to use batch folders
- **BREAKING**: Updated configuration system to use embedded defaults
- **Improved**: Better Blender executable detection and validation
- **Enhanced**: More robust scene file validation and error messages
- **Optimized**: Faster rendering with improved Blender settings
- **Updated**: Dependencies updated to latest stable versions

### Fixed
- Fixed memory leaks in long-running generation sessions
- Corrected annotation precision issues in YOLO format
- Fixed camera positioning edge cases in warehouse mode
- Resolved path handling issues on different operating systems
- Fixed depth map generation inconsistencies

### Removed
- **BREAKING**: Removed legacy separate generator classes (use unified `PalletDataGenerator`)
- Removed deprecated configuration parameters
- Cleaned up redundant utility functions

## [0.1.0] - 2025-09-08

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

## Contributing

For information about contributing to this project, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Support

- 📖 **Documentation**: https://boubakriibrahim.github.io/PalletDataGenerator
- 🐛 **Issues**: https://github.com/boubakriibrahim/PalletDataGenerator/issues
- 💬 **Discussions**: https://github.com/boubakriibrahim/PalletDataGenerator/discussions
- 📦 **PyPI**: https://pypi.org/project/palletdatagenerator/
