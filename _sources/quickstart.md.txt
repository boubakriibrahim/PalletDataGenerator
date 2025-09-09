# Quick Start Guide

This guide will get you up and running with PalletDataGenerator in minutes!

## 🏃‍♂️ 5-Minute Quick Start

### Step 1: Create Virtual Environment

```bash
# Create and activate virtual environment
python3.11 -m venv pallet_env
source pallet_env/bin/activate  # Linux/macOS
# or pallet_env\Scripts\activate  # Windows

# Install the package
pip install palletdatagenerator
```

### Step 2: Prepare Your Blender Scene

Create or open a Blender scene with:
- Objects named with **`pallet`** prefix (e.g., `pallet_01`, `my_pallet`)
- Box template objects named **`box1`**, **`box2`**, **`box3`**

```{note}
See the [Scene Conventions](scenes.md) for detailed requirements.
```

### Step 3: Generate Your First Dataset

#### With Blender (Recommended)
```bash
# Navigate to your Blender scene
cd /path/to/your/scene

# Generate dataset with Blender
blender warehouse_objects.blend --python -m palletdatagenerator.blender_runner -- generate --output ./my_dataset --num-frames 50 --export-format yolo
```

#### Direct Python (Limited)
```python
from palletdatagenerator import PalletDataGenerator
from palletdatagenerator.core.generator import GenerationConfig

# Create generator
generator = PalletDataGenerator()

# Simple configuration
config = GenerationConfig(
    scene_type="single_pallet",
    num_frames=50,
    output_dir="./my_dataset",
    export_formats=["yolo"]
)

# Generate!
results = generator.generate_dataset(config)
print(f"Generated {results['total_frames']} frames!")
```

### Step 4: Check Your Results

```bash
ls ./my_dataset/generated_0001/
# Should contain:
# - images/          (rendered images)
# - annotations/     (YOLO format)
# - dataset_info.json
# - generation.log
```

## 🎯 Common Use Cases

### Single Pallet Scene

Perfect for focused object detection training:

```bash
blender single_pallet.blend --python -m palletdatagenerator.blender_runner -- generate \
  --scene-type single_pallet \
  --num-frames 200 \
  --resolution 640 480 \
  --export-format yolo coco \
  --output ./single_pallet_dataset
```

### Warehouse Environment

Ideal for complex scene understanding:

```bash
blender warehouse.blend --python -m palletdatagenerator.blender_runner -- generate \
  --scene-type warehouse \
  --num-frames 1000 \
  --num-batches 10 \
  --batch-size 100 \
  --resolution 1280 720 \
  --export-format yolo coco voc \
  --gpu \
  --output ./warehouse_dataset
```

### With Custom Configuration

```bash
# Create configuration file
palletdatagenerator config create my_config.yaml --type warehouse

# Edit my_config.yaml to your needs, then:
blender warehouse.blend --python -m palletdatagenerator.blender_runner -- generate \
  --config my_config.yaml \
  --output ./custom_dataset
```

## 📊 Understanding the Output

### Directory Structure

```
my_dataset/
├── generated_0001/           # Batch 1
│   ├── images/
│   │   ├── frame_000001.png
│   │   ├── frame_000002.png
│   │   └── ...
│   ├── annotations/
│   │   ├── yolo/
│   │   │   ├── frame_000001.txt
│   │   │   ├── classes.txt
│   │   │   └── ...
│   │   └── coco/
│   │       ├── annotations.json
│   │       └── ...
│   ├── dataset_info.json
│   └── generation.log
├── generated_0002/           # Batch 2 (if multiple batches)
└── ...
```

### Annotation Formats

#### YOLO Format
```
# classes.txt
pallet
box
hole

# frame_000001.txt
0 0.5 0.3 0.4 0.6    # class_id center_x center_y width height
1 0.2 0.7 0.1 0.15
```

#### COCO Format
```json
{
  "images": [{"id": 1, "file_name": "frame_000001.png", "width": 1280, "height": 720}],
  "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [100, 200, 300, 400]}],
  "categories": [{"id": 1, "name": "pallet"}]
}
```

## 🔧 CLI Command Reference

### Basic Commands

```bash
# Show help
palletdatagenerator --help
palletdatagenerator generate --help

# Show version and system info
palletdatagenerator info --version
palletdatagenerator info --system-info

# Create configuration files
palletdatagenerator config create config.yaml
palletdatagenerator config validate config.yaml

# Setup development environment
palletdatagenerator setup --python-version 3.11
```

### Generation Options

```bash
# Scene types
--scene-type single_pallet    # Single pallet with boxes
--scene-type warehouse        # Multi-pallet warehouse

# Output control
--output ./dataset            # Base output directory
--num-frames 100             # Frames per batch
--batch-size 100             # Frames per batch
--num-batches 5              # Number of batches

# Quality settings
--resolution 1280 720        # Image resolution
--samples 128                # Rendering samples (quality)
--gpu                        # Use GPU acceleration
--fast-mode                  # Lower quality, faster rendering

# Export formats
--export-format yolo         # YOLO format
--export-format coco         # COCO format
--export-format voc          # PASCAL VOC format
--export-format yolo coco voc # Multiple formats

# Advanced features
--background-images-dir ./backgrounds  # Random backgrounds
--analysis-images            # Debug visualizations
--depth-maps                # Depth information
--segmentation-masks        # Instance masks
```

## 🎨 Blender Integration

### Scene Setup Requirements

Your Blender scene must follow these conventions:

```{important}
**Required Objects:**
- Objects with `pallet` in the name (e.g., `pallet`, `pallet_01`)
- Box templates named `box1`, `box2`, `box3`
- Proper scale (metric units, applied transforms)
```

### Launch Commands

```bash
# Basic launch
blender scene.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset

# Background mode (no GUI)
blender --background scene.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset

# With custom Python path
blender scene.blend --python-use-system-env --python -m palletdatagenerator.blender_runner -- generate --output ./dataset
```

### Environment Variables

```bash
# Set Python path for Blender
export PYTHONPATH="/path/to/your/pallet_env/lib/python3.11/site-packages:$PYTHONPATH"

# Run with environment
blender scene.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset
```

## 🚨 Troubleshooting Quick Fixes

### Common Issues

#### 1. "No pallet objects found"
```bash
# Check your scene objects in Blender
# Ensure objects have 'pallet' in their names
```

#### 2. "Module not found" errors
```bash
# Ensure virtual environment is activated
source pallet_env/bin/activate

# Check Python path
python -c "import sys; print(sys.path)"
```

#### 3. GPU not detected
```bash
# Check GPU availability
palletdatagenerator info --system-info

# Force CPU if needed
blender scene.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset  # (GPU auto-detected)
```

#### 4. Empty output directory
```bash
# Check logs
cat ./dataset/generated_0001/generation.log

# Run with verbose output
blender scene.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset --verbose
```

## 📈 Performance Tips

### Speed Optimization

```bash
# Fast mode for testing
--fast-mode --samples 32

# Use GPU
--gpu

# Smaller resolution for testing
--resolution 640 480

# Batch processing
--num-batches 10 --batch-size 100
```

### Quality Optimization

```bash
# High quality
--samples 256 --resolution 1920 1080

# Enable denoising
--denoiser AUTO

# Multiple export formats
--export-format yolo coco voc
```

## 🎯 Next Steps

Now that you have the basics:

1. **Explore [Configuration Options](configuration.md)**
2. **Check out [Advanced Examples](examples/index.md)**
3. **Read about [Scene Setup](scenes.md)**
4. **Learn [Best Practices](best_practices.md)**

## 💡 Pro Tips

- **Start small**: Begin with 10-50 frames to test your setup
- **Use batches**: Large datasets are easier to manage in batches
- **Monitor logs**: Check `generation.log` for detailed information
- **GPU acceleration**: Significantly speeds up rendering
- **Scene validation**: Ensure your scene meets the requirements

---

**Happy generating! 🚀 Ready to create some amazing datasets!**
