# Installation Guide

## 🚀 System Requirements

### Recommended Versions (Tested & Optimized)
- **Python**: 3.11.13
- **Blender**: 4.5.1 LTS

### Minimum Requirements
- **Python**: 3.11
- **Blender**: 4.5
- **RAM**: 8GB (16GB+ recommended)
- **GPU**: NVIDIA, AMD, or Apple Silicon (optional but recommended)

## 📦 Installation Methods

### Method 1: PyPI Installation (Recommended)

```bash
# Install from PyPI
pip install palletdatagenerator

# Verify installation
python -c "import palletdatagenerator; print(palletdatagenerator.__version__)"
```

### Method 2: Development Installation

```bash
# Clone repository
git clone https://github.com/boubakriibrahim/PalletDataGenerator.git
cd PalletDataGenerator

# Create virtual environment
python3.11 -m venv pallet_env

# Activate virtual environment
source pallet_env/bin/activate  # Linux/macOS
# or
pallet_env\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"
```

### Method 3: Using the Built-in Setup Command

```bash
# Automated setup (creates virtual environment and installs)
python -m palletdatagenerator setup --python-version 3.11 --venv-name pallet_env

# Follow the printed instructions to activate and use
```

## 🎨 Blender Setup

### Installing Blender

#### macOS
```bash
# Using Homebrew
brew install --cask blender

# Or download from https://www.blender.org/download/
```

#### Linux (Ubuntu/Debian)
```bash
# Using apt
sudo apt update
sudo apt install blender

# Or using snap
sudo snap install blender --classic
```

#### Windows
1. Download from [blender.org](https://www.blender.org/download/)
2. Run the installer
3. Add Blender to PATH (optional but recommended)

### Verifying Blender Installation

```bash
# Check Blender version
blender --version

# Test Python integration
blender --background --python-expr "import sys; print(f'Python {sys.version}')"
```

## 🔧 Virtual Environment Setup

### Creating a Virtual Environment

```bash
# Python 3.11 (recommended)
python3.11 -m venv pallet_env

# Or use your default Python
python -m venv pallet_env
```

### Activating the Virtual Environment

#### Linux/macOS
```bash
source pallet_env/bin/activate
```

#### Windows
```bash
# Command Prompt
pallet_env\Scripts\activate

# PowerShell
pallet_env\Scripts\Activate.ps1
```

### Installing Dependencies

```bash
# Basic installation
pip install palletdatagenerator

# Development installation with all extras
pip install "palletdatagenerator[dev,docs,gpu]"

# From source
pip install -e ".[dev]"
```

## 🧪 Verification

### Quick Test

```python
# Test basic import
from palletdatagenerator import PalletDataGenerator
from palletdatagenerator.core.generator import GenerationConfig

print("✅ PalletDataGenerator installed successfully!")

# Test configuration
config = GenerationConfig(
    scene_type="single_pallet",
    num_frames=1,
    resolution=(640, 480),
    output_dir="./test_output"
)
print("✅ Configuration system working!")
```

### Blender Integration Test

```bash
# Test with Blender (create a simple scene first)
blender --background --python -c "
import sys
sys.path.append('path/to/your/pallet_env/lib/python3.11/site-packages')
from palletdatagenerator.blender_runner import BlenderEnvironmentManager
env = BlenderEnvironmentManager()
print('✅ Blender integration working!' if env.blender_available else '❌ Blender integration failed')
"
```

### CLI Test

```bash
# Test CLI
palletdatagenerator info --version
palletdatagenerator info --system-info

# Test configuration creation
palletdatagenerator config create example_config.yaml
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Python Version Compatibility

```bash
# Check Python version
python --version

# If using wrong Python version, specify explicitly
python3.11 -m pip install palletdatagenerator
```

#### 2. Blender Python Path Issues

```bash
# Find Blender's Python path
blender --background --python-expr "import sys; print(sys.executable)"

# Install package for Blender's Python
/path/to/blender/python -m pip install palletdatagenerator
```

#### 3. GPU Issues

```bash
```python
# Check GPU availability
from palletdatagenerator.blender_runner import BlenderEnvironmentManager
env = BlenderEnvironmentManager()
env.setup_blender_preferences(use_gpu=True)
```

#### 4. Import Errors

```bash
# Reinstall with force
pip uninstall palletdatagenerator
pip install --no-cache-dir palletdatagenerator

# Check installation
pip show palletdatagenerator
```

### Platform-Specific Issues

#### macOS

```bash
# Fix SSL certificates (if needed)
/Applications/Python\ 3.11/Install\ Certificates.command

# Apple Silicon specific
arch -arm64 pip install palletdatagenerator
```

#### Linux

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-dev build-essential

# Fix permissions (if needed)
sudo chown -R $USER:$USER ~/.local
```

#### Windows

```powershell
# Run as Administrator if needed
# Install Visual C++ Build Tools if compilation errors occur
```

## 📚 Next Steps

After successful installation:

1. **Read the [Quick Start Guide](quickstart.md)**
2. **Try the [Examples](examples/index.md)**
3. **Configure your [Settings](configuration.md)**
4. **Join the [Community](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)**

## 🆘 Getting Help

If you encounter issues:

1. **Check the [FAQ](faq.md)**
2. **Search [Existing Issues](https://github.com/boubakriibrahim/PalletDataGenerator/issues)**
3. **Create a [New Issue](https://github.com/boubakriibrahim/PalletDataGenerator/issues/new)**
4. **Join [Discussions](https://github.com/boubakriibrahim/PalletDataGenerator/discussions)**

---

**Installation complete! 🎉 Ready to generate some datasets!**
