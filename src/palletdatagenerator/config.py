"""
Configuration file for PalletDataGenerator.
Combines settings from original one_pallet_generator.py and warehouse_generator.py
"""

import glob
import os
import re
from dataclasses import dataclass

# Default directories (updated for new structure)
BASE_OUTPUT_DIR = "output"  # Base output directory
DEFAULT_BG_DIR = "backgrounds"  # Default background images directory


def get_next_batch_folder(base_output_dir: str, mode: str) -> str:
    """
    Automatically detect existing generated_XXXXXX folders and create the next batch folder.

    Returns the full path to the new batch folder: output/{mode}/generated_XXXXXX/
    """
    # Create mode directory if it doesn't exist
    mode_dir = os.path.join(base_output_dir, mode)
    os.makedirs(mode_dir, exist_ok=True)

    # Look for existing generated_XXXXXX folders
    pattern = os.path.join(mode_dir, "generated_*")
    existing_folders = glob.glob(pattern)

    # Extract numbers from folder names
    max_num = 0
    for folder in existing_folders:
        folder_name = os.path.basename(folder)
        match = re.match(r"generated_(\d+)", folder_name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    # Create next batch folder
    next_num = max_num + 1
    batch_folder_name = f"generated_{next_num:06d}"
    batch_folder_path = os.path.join(mode_dir, batch_folder_name)

    print(f"[INFO] Creating batch folder: {batch_folder_path}")
    os.makedirs(batch_folder_path, exist_ok=True)

    return batch_folder_path


# Single pallet CONFIG (EXACT from original one_pallet_generator.py)
SINGLE_PALLET_CONFIG = {
    # root
    "output_dir": BASE_OUTPUT_DIR,
    "num_images": 50,
    "render_engine": "CYCLES",
    "resolution_x": 640,
    "resolution_y": 640,
    # camera
    "camera_focal_mm": 35.0,
    "camera_sensor_mm": 36.0,
    "side_face_probability": 0.9,
    "preferred_face_angles": {
        "front": (0, 45),
        "back": (135, 225),
        "left": (45, 135),
        "right": (225, 315),
    },
    # cropping/occlusion
    "allow_cropping": True,
    "min_visible_area_ratio": 0.3,
    "max_crop_ratio": 0.7,
    # environment
    "add_floor": True,
    "randomize_background": False,  # stable world is faster
    "background_types": ["solid", "gradient"],
    "real_background_images_dir": DEFAULT_BG_DIR,
    "use_real_background": False,
    "depth_scale": 1000.0,
    "generate_analysis": True,
    # scene control
    "static_scene": True,
    "apply_initial_random_transform": False,
    "save_scene_before_render": False,  # Save generated scene to scenes folder
    # pallet XY motion (optional)
    "allow_pallet_move_xy": False,
    "pallet_move_x_range": (-0.2, 0.2),
    "pallet_move_y_range": (-0.2, 0.2),
    # duplicate pallets
    "duplicate_pallets": False,
    "num_pallets": 2,
    # Probability-driven stacking: per-scene chance to create a stacked pallet setup
    "stacked_pallets_probability": 0.5,  # 50% chance per frame to stack pallets
    "stacked_pallets_max": 4,  # Max number of stacked pallets (random 2 to max)
    "pallet_stack_vertical": True,
    "pallet_stack_gap": 0.0,
    "unique_object_index": True,
    # camera ground safety
    "prevent_camera_below_ground": True,
    "assumed_ground_z": -1.0,
    "camera_min_z_above_ground": 0.05,
    # FAST mode
    "fast_mode": True,
    "fast_samples": 8,  # ULTRA low samples for maximum speed, denoiser will clean it
    "fast_denoiser": "AUTO",  # AUTO: Metal->OIDN, CUDA->OPTIX
    "fast_adaptive_sampling": True,
    "cycles_persistent_data": True,
    # GPU backend preference (CUDA for H100, OPTIX for RTX cards, METAL for macOS)
    "_gpu_backend": "CUDA",  # Prefer CUDA on H100 (lacks RT cores), can override with PALLET_GPU_BACKEND env var
    # Performance: Disable slow post-processing for speed
    "generate_analysis_images": True,  # Analysis images are slow, disable for production
    "generate_depth_normals_index": True,  # Depth/normals/index passes are slow, disable for speed
    "analysis_show_all_labels": True,  # Only used if generate_analysis_images=True
    # ---------------- Lighting randomness ----------------
    "randomize_lights_per_frame": False,
    "light_count_range": (2, 4),  # Increased minimum from 1 to 2 lights
    "light_types": ["POINT", "AREA", "SPOT", "SUN"],
    "light_energy_ranges": {
        "POINT": (200, 500),  # Increased from (50, 300)
        "AREA": (150, 400),  # Increased from (30, 200)
        "SPOT": (600, 1500),  # Increased from (300, 1200)
        "SUN": (4, 10),  # Increased from (2, 8)
    },
    "light_distance_range": (2.0, 6.0),
    "light_elevation_deg_range": (10.0, 80.0),
    "use_colored_lights": False,
    "colored_light_probability": 0.6,
    "light_color_palette": [
        (1.0, 1.0, 1.0, 1.0),
        (1.0, 0.95, 0.85, 1.0),
        (0.85, 0.9, 1.0, 1.0),
        (1.0, 0.6, 0.4, 1.0),
        (0.6, 0.8, 1.0, 1.0),
        (0.9, 0.7, 1.0, 1.0),
        (0.8, 1.0, 0.6, 1.0),
    ],
    "spot_size_deg_range": (20.0, 50.0),
    "spot_blend_range": (0.1, 0.4),
    # --------- Realism helpers to prevent dark frames ---------
    "force_key_light": True,  # ensure at least one bright white key light (Default True in original)
    "min_key_light_energy": 800.0,  # Increased from 500.0 - watts-ish (for SPOT/AREA); SUN uses small strengths
    "min_total_light_energy": 600.0,  # Increased from 300.0 - minimum total lighting energy to prevent dark frames
    "world_min_strength": 0.5,  # Increased from 0.2 - minimum background light strength (Filmic + low key)
    # --------- Auto exposure (per-frame) ----------
    "enable_auto_exposure": True,
    "target_luminance": 0.18,  # aim for 18% gray average luminance
    "exposure_min": -1.0,  # Changed from -2.0 - less negative to prevent very dark frames
    "exposure_max": 4.0,
    "exposure_smooth": 0.6,  # 0..1 how strongly to apply EV correction
    "preview_samples": 1,  # Reduced from 4 to 1 for maximum speed (preview is just for exposure measurement)
    "preview_resolution_percent": 50,  # Render preview at 50% resolution for speed
    "initial_exposure_ev": 0.0,  # starting EV
    # Name of an auxiliary object that moves with pallet but is not annotated
    "attached_box_name": "box",
    # --------------- Pallet variant randomization ---------------
    "randomize_pallet_variant": True,  # Enable pallet variant swapping
    "pallet_variant_change_probability": 0.5,
    "pallet_variant_names": [
        "pallet.001",
        "pallet.002",
        "pallet.003",
        "pallet.004",
        "pallet.005",
    ],
    # --------------- Attached box randomization ---------------
    "attached_box_variants": ["box1", "box2", "box3"],
    "randomize_attached_box_per_frame": True,
    "attached_box_group": True,
    "attached_box_group_count_range": (2, 4),
    "attached_box_allow_extra_height": (1.0, 1.6),
    "hide_placeholder_box": True,
    "attached_box_enable_stacking": True,
    "attached_box_stack_probability": 0.6,
    "attached_box_stack_layers_range": (2, 4),
    "attached_box_stack_offset_factor": 0.05,
    # --------------- Box material randomization ---------------
    "randomize_box_materials": True,  # DISABLED temporarily - Enable random material loading from blend files
    "box_materials_path": "scenes/assets/materials/boxes",  # Path to folder containing material blend files
    "box_material_probability": 0.25,  # Probability to apply random material to each box (1.0 = always)
    # --------------- Keypoints Generation ---------------
    "generate_keypoints": True,
    "keypoints_min_face_area": 80,  # Minimum face area to generate keypoints
    "keypoints_visibility_check": False,  # Enable ray casting for visibility
    "keypoints_face_detection_threshold": 0.5,  # Confidence threshold for face detection
    "keypoints_show_3d_labels": False,  # Show 3D coordinate labels in analysis images
    "keypoints_show_2d_labels": False,  # Show 2D coordinate labels in analysis images
    "keypoints_show_labels": True,  # Show all keypoint labels (names, coordinates) in analysis images
    "analysis_show_all_labels": False,  # Show all labels in analysis images (YOLO boxes, 3D structures)
    "analysis_show_keypoints": True,  # Show keypoints in analysis images
    "analysis_show_2d_boxes": True,  # Show 2D bounding boxes of selected faces in analysis images
    "analysis_show_3d_coordinates": False,  # Show 3D coordinates of selected faces in analysis images
    # --------------- Output folder generation ---------------
    "generate_debug_3d": True,  # Generate debug_3d folder with 3D visualizations
    "generate_voc_xml": False,  # Generate VOC XML annotations
}


# Warehouse CONFIG (from warehouse_generator.py)
WAREHOUSE_CONFIG = {
    # Base parameters
    "output_dir": BASE_OUTPUT_DIR,
    "num_scenes": 3,
    "max_images_per_scene": 15,
    "max_total_images": 50,
    # Render quality
    "resolution_x": 640,
    "resolution_y": 640,
    "render_engine": "CYCLES",
    "fast_samples": 8,  # ULTRA low samples for maximum speed, denoiser will clean it
    "fast_mode": True,
    "fast_denoiser": "AUTO",
    # Performance: Disable slow post-processing for speed
    "generate_analysis_images": False,  # Analysis images are slow, disable for production
    "generate_depth_normals_index": False,  # Depth/normals/index passes are slow, disable for speed
    # Forklift simulation
    "camera_focal_mm": 35.0,
    "camera_sensor_mm": 36.0,
    "camera_height_range_m": (1.4, 2.0),
    "camera_height_range": (1.4, 2.0),
    "camera_lateral_jitter_m": 0.15,
    "camera_yaw_jitter_deg": 3.0,
    "camera_pitch_deg_range": (-3.0, 8.0),
    "camera_forward_step_m": (0.3, 0.8),
    "camera_path_variation": 0.5,
    # Scene randomization
    "box_removal_probability": 0.7,
    "pallet_groups_to_fill": (5, 7),
    "object_position_variation": 0.05,
    # Generation options
    "generate_analysis": True,
    "generate_segmentation": True,
    "save_scene_before_render": True,
    # Detection
    "max_faces_per_pallet": 2,
    "min_pallet_area": 100,
    "min_visible_area_ratio": 0.2,
    "allow_cropping": True,
    # Lighting
    "randomize_lights_per_frame": True,
    "light_count_range": (2, 4),
    "use_colored_lights": True,
    "colored_light_probability": 0.3,
    "light_energy_ranges": {
        "POINT": (100, 500),
        "AREA": (50, 300),
        "SPOT": (500, 2000),
        "SUN": (3, 10),
    },
    # Auto exposure
    "enable_auto_exposure": True,
    "target_luminance": 0.18,
    "exposure_min": -2.0,
    "exposure_max": 2.0,
    # --------------- Keypoints Generation ---------------
    "generate_keypoints": True,
    "keypoints_min_face_area": 80,  # Minimum face area to generate keypoints
    "keypoints_visibility_check": False,  # Enable ray casting for visibility
    "keypoints_face_detection_threshold": 0.5,  # Confidence threshold for face detection
    "keypoints_show_3d_labels": False,  # Show 3D coordinate labels in analysis images
    "keypoints_show_2d_labels": False,  # Show 2D coordinate labels in analysis images
    "keypoints_show_labels": True,  # Show all keypoint labels (names, coordinates) in analysis images
    "analysis_show_all_labels": False,  # Show all labels in analysis images (YOLO boxes, 3D structures)
    "analysis_show_keypoints": True,  # Show keypoints in analysis images
    "analysis_show_2d_boxes": True,  # Show 2D bounding boxes of selected faces in analysis images
    "analysis_show_3d_coordinates": False,  # Show 3D coordinates of selected faces in analysis images
    # --------------- Output folder generation ---------------
    "generate_debug_3d": True,  # Generate debug_3d folder with 3D visualizations
    "generate_voc_xml": False,  # Generate VOC XML annotations
}


@dataclass
class DefaultConfig:
    """Configuration class that adapts based on mode."""

    def __init__(self, mode: str = "single_pallet"):
        """Initialize config based on mode."""
        self.mode = mode

        if mode == "single_pallet":
            self._config = SINGLE_PALLET_CONFIG.copy()
        elif mode == "warehouse":
            self._config = WAREHOUSE_CONFIG.copy()
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def __getattr__(self, name):
        """Allow dict-style access to config values."""
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        return self._config.get(name)

    def __setattr__(self, name, value):
        """Allow setting config values."""
        if name.startswith("_") or name == "mode":
            object.__setattr__(self, name, value)
        else:
            if hasattr(self, "_config"):
                self._config[name] = value
            else:
                object.__setattr__(self, name, value)

    def get(self, key, default=None):
        """Dict-style get method."""
        return self._config.get(key, default)

    def update(self, **kwargs):
        """Update multiple config values."""
        self._config.update(kwargs)
