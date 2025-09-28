# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2025-01-15

### Added
- **🎯 Advanced Keypoints Generation**: Automatic face detection with 6 keypoints per selected face
  - **Selective face detection**: Detects 1-2 most visible faces from the pallet (not all faces)
  - **6 keypoints per selected face**: 2 middle (top-down), 2 left (top-down), 2 right (top-down)
  - **Visibility tracking**: Ray casting for occlusion detection between face and camera
  - **YOLO format output**: Normalized coordinates with visibility flags (2=visible, 0=hidden)
  - **Analysis visualization**: Keypoints with different colors for visible/hidden states
- **🔍 3D Debug Visualization**: Comprehensive debugging tools for keypoints analysis
  - **Interactive HTML figures**: Real-time 3D visualization using Plotly.js
  - **Face selection analysis**: Shows which faces were chosen and why
  - **Camera positioning**: Distance calculations to each face with visual lines
  - **Coordinate tracking**: Detailed 3D coordinate information for debugging
  - **Debug output structure**: `debug_3d/` folder with coordinates, figures, and images
- **📊 Enhanced Output Structure**: New directories for comprehensive debugging
  - `keypoints_labels/`: YOLO format keypoints annotations
  - `face_2d_boxes/`: 2D bounding boxes for detected faces
  - `face_3d_coordinates/`: 3D coordinates for keypoints
  - `debug_3d/coordinates/`: Detailed coordinate information
  - `debug_3d/figures/`: Interactive HTML 3D figures
  - `debug_3d/images/`: 3D debug visualization images
- **🎮 Interactive 3D Visualization**: Real-time exploration tools
  - **Interactive controls**: Rotate, zoom, pan, reset view
  - **Color-coded elements**: Red corners, blue camera, gray distance lines, green/orange selected faces
  - **Face highlighting**: Selected faces in green/orange, unselected in blue
  - **Camera visualization**: Green diamond showing camera position with distance lines
- **📚 Comprehensive Documentation**: Updated guides and examples
  - **Keypoints Generation Guide**: Detailed documentation in `docs/keypoints_generation.md`
  - **Real examples**: Actual data from generated datasets
  - **Interactive examples**: Working HTML visualizations with real data
  - **Usage instructions**: Step-by-step guides for debug 3D features

### Changed
- **Enhanced Configuration**: Added keypoints generation options to both single pallet and warehouse configs
  - `generate_keypoints`: Enable/disable keypoints generation
  - `keypoints_min_face_area`: Minimum face area threshold
  - `keypoints_visibility_check`: Enable ray casting for visibility
  - `keypoints_show_3d_labels`: Show 3D coordinate labels in analysis
  - `keypoints_show_2d_labels`: Show 2D coordinate labels in analysis
  - `analysis_show_keypoints`: Show keypoints in analysis images
  - `analysis_show_2d_boxes`: Show 2D bounding boxes in analysis
  - `analysis_show_3d_coordinates`: Show 3D coordinates in analysis
- **Updated Dependencies**: Added matplotlib and plotly for 3D visualization
- **Enhanced Analysis Images**: Now include keypoints visualization with color-coded visibility
- **Improved Metadata**: Face and keypoint information included in dataset manifest

### Fixed
- **Face Detection Accuracy**: Improved face selection criteria for better keypoints generation
- **Coordinate Precision**: Enhanced 3D coordinate calculations for accurate keypoint placement
- **Visibility Detection**: Fixed ray casting implementation for proper occlusion detection
- **Analysis Image Generation**: Corrected keypoints visualization in analysis overlays

### Technical Details
- **Face Detection Algorithm**: Scans for objects with "face" in their name, extracts side faces from 3D bounding box
- **Keypoint Layout**: 6 keypoints per face - 4 corners + 2 middle points (top and bottom center)
- **Visibility System**: Uses ray casting to detect obstacles between camera and keypoints
- **3D Visualization**: Plotly.js-based interactive 3D scenes with real-time manipulation
- **Debug Information**: Comprehensive coordinate tracking with face selection reasoning

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
