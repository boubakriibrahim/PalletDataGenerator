# Keypoints Generation Feature

This document describes the keypoints generation feature added to PalletDataGenerator, which automatically detects faces in the scene and generates 6 keypoints per face with visibility tracking.

## Overview

The keypoints generation system:
- **Detects faces** in the Blender scene by looking for pallet objects and extracting their side faces
- **Generates 6 keypoints** per face: 4 corners of the 3D face + 2 middle points (top and bottom center)
- **Tracks visibility** of each keypoint using ray casting to detect obstacles
- **Saves labels** in YOLO format to the `keypoints_labels` folder
- **Visualizes keypoints** in analysis images with different colors for visible/hidden points
- **3D Debug Visualization** with interactive HTML figures and detailed coordinate tracking
- **Comprehensive metadata** including face selection criteria and camera positioning

## Keypoints Layout

Each face gets 6 keypoints arranged as follows:

```
    Top Left (2)     Middle Top (0)     Top Right (4)
           |                |                |
           |                |                |
    Bottom Left (3)  Middle Bottom (1)  Bottom Right (5)
```

- **Middle keypoints**: Top and bottom center of the face (calculated as midpoints between corners)
- **Corner keypoints**: The 4 actual corners of the 3D face (top-left, top-right, bottom-left, bottom-right)

## Configuration

Add these settings to your config to control keypoints generation:

```python
config = {
    # Enable/disable keypoints generation
    "generate_keypoints": True,
    
    # Minimum face area (in pixels) to generate keypoints
    "keypoints_min_face_area": 100,
    
    # Enable ray casting for visibility detection
    "keypoints_visibility_check": True,
    
    # Face detection confidence threshold
    "keypoints_face_detection_threshold": 0.5,
    
    # Show 3D coordinate labels in analysis images
    "keypoints_show_3d_labels": True,
    
    # Show 2D coordinate labels in analysis images
    "keypoints_show_2d_labels": True,
    
    # Show all keypoint labels (names, coordinates) in analysis images
    "keypoints_show_labels": True,
    
    # Show all labels in analysis images (YOLO boxes, 3D structures)
    "analysis_show_all_labels": True,
    
    # Show keypoints in analysis images
    "analysis_show_keypoints": True,
}
```

## Output Format

### Keypoints Labels (YOLO Format)

Keypoints are saved in YOLO format in the `keypoints_labels` folder:

```
class_id x_center y_center width height kp1_x kp1_y kp1_v kp2_x kp2_y kp2_v ...
```

Where:
- `class_id`: Object class (0 for face)
- `x_center, y_center`: Face bounding box center (normalized 0-1)
- `width, height`: Face bounding box dimensions (normalized 0-1)
- `kpN_x, kpN_y`: Keypoint coordinates (normalized 0-1) - always provided regardless of visibility
- `kpN_v`: Visibility flag (2=visible, 0=hidden)

### Example Keypoints File

```
0 0.573150 0.639442 0.284453 0.139362 0.580366 0.603590 2 0.578420 0.669213 2 0.715376 0.569761 2 0.710409 0.633069 2 0.430924 0.641035 2 0.432683 0.709123 2
```

This represents:
- Face at center (0.573, 0.639) with size 0.284×0.139
- All 6 keypoints visible (visibility=2)
- **Real example** from generated dataset with actual face detection results

## Analysis Images

Analysis images show keypoints visualization:
- **Colored circles**: Visible keypoints (different colors for different faces)
- **Gray circles with X**: Hidden keypoints
- **White text**: Keypoint names (if `keypoints_show_labels` is enabled)
- **Orange text**: 3D coordinates (if both `keypoints_show_labels` and `keypoints_show_3d_labels` are enabled)
- **Cyan text**: 2D coordinates (if both `keypoints_show_labels` and `keypoints_show_2d_labels` are enabled)
- **Legend**: Shows what each color represents

**Label Control:**
- Set `analysis_show_all_labels: False` to hide YOLO boxes and 3D structures
- Set `analysis_show_keypoints: False` to hide keypoints completely
- Set `keypoints_show_labels: False` to hide ALL keypoint labels (names and coordinates)
- Set `keypoints_show_3d_labels: False` to hide only 3D coordinate labels
- Set `keypoints_show_2d_labels: False` to hide only 2D coordinate labels

**Face Colors:**
- Face 0: Red keypoints
- Face 1: Green keypoints  
- Face 2: Blue keypoints
- Face 3: Yellow keypoints

**Usage Examples:**
```python
# Hide YOLO boxes and 3D structures, show only keypoints
"analysis_show_all_labels": False,
"analysis_show_keypoints": True

# Show YOLO boxes and 3D structures, hide keypoints
"analysis_show_all_labels": True,
"analysis_show_keypoints": False

# Show everything
"analysis_show_all_labels": True,
"analysis_show_keypoints": True

# Hide everything
"analysis_show_all_labels": False,
"analysis_show_keypoints": False
```

## Usage Example

```python
from palletdatagenerator import PalletDataGenerator

# Create generator
generator = PalletDataGenerator(mode="single_pallet")

# Configure keypoints
config_updates = {
    "generate_keypoints": True,
    "keypoints_min_face_area": 100,
    "generate_analysis": True,  # To see keypoints visualization
}

# Generate dataset
result = generator.generate(
    num_frames=50,
    resolution=(640, 480)
)

print(f"Generated {result['frames_generated']} frames")
print(f"Keypoints saved to: {result['output_dir']}/keypoints_labels/")
```

## Face Detection

The system detects faces by:
1. Looking for pallet objects (mesh objects with "pallet" in their name or pass_index > 0)
2. Extracting the 4 side faces from each pallet's 3D bounding box (excludes top/bottom faces)
3. Checking if each face is visible from the camera
4. Verifying the face meets minimum area requirements
5. Selecting up to 2 most visible faces that are well-oriented to the camera
6. Generating keypoints for each selected face

To add faces to your scene:
- Create pallet objects (mesh objects with "pallet" in their name)
- Ensure they're visible from the camera
- The system will automatically extract side faces and generate keypoints

## Visibility Detection

Keypoint visibility is determined by:
1. **Camera frustum check**: Keypoint must be in front of camera
2. **Ray casting**: Line-of-sight check from camera to keypoint
3. **Obstacle detection**: Objects blocking the view are detected

Visibility values:
- `2`: Keypoint is visible and not occluded
- `0`: Keypoint is hidden or occluded

## 3D Debug Visualization

The system generates comprehensive 3D debug information in the `debug_3d` folder:

### Debug Output Structure
```
debug_3d/
├── coordinates/           # Detailed coordinate information
│   └── frame_XXXXXX_coordinates.txt
├── figures/              # Interactive HTML 3D figures
│   └── frame_XXXXXX_3d_interactive.html
└── images/               # 3D debug visualization images
    └── frame_XXXXXX_3d_debug.png
```

### Coordinate Files
Each frame generates a detailed coordinate file containing:
- **Camera position** and orientation
- **All face definitions** with corner coordinates
- **Selected faces** with selection criteria
- **Distance calculations** from camera to each face
- **2D and 3D bounding boxes** for each face
- **Face selection status** and reasoning

### Interactive HTML Figures
- **3D visualization** of the entire scene using Plotly.js
- **Interactive controls**: rotate, zoom, pan, reset view
- **Face highlighting**: selected faces in red, unselected in blue
- **Keypoint visualization**: 6 keypoints per selected face (orange dots)
- **Camera position**: green diamond showing camera location
- **Real-time distance calculations** from camera to each face
- **Legend and controls** for easy navigation and understanding

### Debug Images
- **Static 3D visualization** for quick reference
- **Face selection visualization** showing which faces were chosen
- **Coordinate system reference** for debugging

## Using Debug 3D Features

### Interactive HTML Visualization
1. **Open the HTML file** in any modern web browser
2. **Navigate the 3D scene**:
   - **Rotate**: Click and drag to rotate the view
   - **Zoom**: Use mouse wheel to zoom in/out
   - **Pan**: Right-click and drag to pan the view
   - **Reset**: Double-click to reset to default view
3. **Analyze face selection**:
   - **Red faces**: Selected for keypoints generation
   - **Blue faces**: Detected but not selected
   - **Orange dots**: Generated keypoints (6 per selected face)
   - **Green diamond**: Camera position

### Coordinate Analysis
The coordinate files provide detailed information for debugging:
- **Face selection criteria**: Why certain faces were chosen
- **Distance calculations**: Camera-to-face distances for selection
- **Bounding box data**: Both 2D and 3D bounding box information
- **Keypoint positions**: Exact 3D coordinates of all keypoints

### Example Usage
```bash
# Generate dataset with debug 3D enabled
palletgen -m single_pallet scenes/one_pallet.blend --frames 10

# View debug files
ls output/single_pallet/generated_XXXXXX/debug_3d/
# coordinates/  figures/  images/

# Open interactive 3D visualization
open output/single_pallet/generated_XXXXXX/debug_3d/figures/frame_000000_3d_interactive.html

# View coordinate details
cat output/single_pallet/generated_XXXXXX/debug_3d/coordinates/frame_000000_coordinates.txt
```

## Integration with Existing Features

Keypoints generation integrates seamlessly with:
- **Analysis images**: Keypoints are visualized alongside bounding boxes
- **Metadata**: Face and keypoint information is included in dataset manifest
- **YOLO labels**: Keypoints follow YOLO format standards
- **Configuration**: All settings are configurable via config file
- **3D Debug**: Comprehensive visualization and coordinate tracking

## Troubleshooting

### No keypoints generated
- Check that objects have "face" in their name
- Verify objects are mesh type
- Ensure objects are visible from camera
- Check minimum area threshold setting

### All keypoints marked as hidden
- Verify camera positioning
- Check for objects blocking the view
- Ensure face objects are not behind camera
- Try disabling visibility check for testing

### Keypoints in wrong positions
- Verify face object geometry
- Check face object orientation
- Ensure face object has proper bounding box

## Advanced Configuration

For advanced users, you can customize:
- Keypoint positioning relative to face geometry
- Visibility detection algorithms
- Face detection criteria
- Output format and coordinate systems

See the source code in `modes/base_generator.py` for implementation details.