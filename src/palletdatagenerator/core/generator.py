"""Core generator classes for pallet and warehouse dataset generation."""

import colorsys
import math
import os
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import bpy
    from bpy_extras.object_utils import world_to_camera_view as w2cv
    from mathutils import Euler, Matrix, Vector

    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False

    # Mock classes for type hints when Blender is not available
    class Vector:
        def __init__(self, *args):
            pass

    class Matrix:
        def __init__(self, *args):
            pass

    class Euler:
        def __init__(self, *args):
            pass

    w2cv = None


@dataclass
class GenerationConfig:
    """Configuration class for dataset generation.

    Attributes:
        output_dir: Directory to save generated datasets
        num_images: Number of images to generate
        resolution: Tuple of (width, height) for output resolution
        render_engine: Blender render engine ('CYCLES' or 'EEVEE')
        camera_config: Camera settings dictionary
        lighting_config: Light randomization settings
        export_formats: List of export formats ('yolo', 'coco', 'voc')
    """

    output_dir: str = "outputs"
    num_images: int = 50
    resolution: tuple[int, int] = (1280, 720)
    render_engine: str = "CYCLES"
    camera_config: dict[str, Any] = field(default_factory=dict)
    lighting_config: dict[str, Any] = field(default_factory=dict)
    export_formats: list[str] = field(default_factory=lambda: ["yolo", "coco"])

    def __post_init__(self):
        """Initialize default configurations if not provided."""
        if not self.camera_config:
            self.camera_config = {
                "focal_mm": 35.0,
                "sensor_mm": 36.0,
                "height_range": (1.0, 3.0),
            }

        if not self.lighting_config:
            self.lighting_config = {
                "randomize_per_frame": True,
                "light_count_range": (2, 4),
                "use_colored_lights": True,
                "colored_light_probability": 0.6,
            }


class BaseGenerator:
    """Base class for dataset generators.

    Provides common functionality for Blender-based synthetic dataset generation
    including GPU configuration, rendering setup, and utility methods.
    """

    def __init__(self, config: GenerationConfig):
        """Initialize the generator with configuration.

        Args:
            config: Generation configuration object

        Raises:
            RuntimeError: If Blender is not available
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError(
                "Blender Python API not available. This library must be run within Blender."
            )

        self.config = config
        self.scene = bpy.context.scene
        self._setup_directories()

    def _setup_directories(self) -> dict[str, str]:
        """Create output directory structure.

        Returns:
            Dictionary mapping directory types to paths
        """
        base_dir = Path(self.config.output_dir)
        directories = {
            "images": base_dir / "images",
            "depth": base_dir / "depth",
            "normals": base_dir / "normals",
            "index": base_dir / "index",
            "analysis": base_dir / "analysis",
            "yolo_labels": base_dir / "yolo_labels",
            "voc_xml": base_dir / "voc_xml",
        }

        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        return {k: str(v) for k, v in directories.items()}

    def enable_gpu(self, preferred: str | None = None) -> str:
        """Enable GPU rendering with platform-aware backend selection.

        Args:
            preferred: Preferred GPU backend (optional)

        Returns:
            Name of selected backend or 'CPU' if no GPU available
        """
        prefs = bpy.context.preferences
        if "cycles" not in prefs.addons:
            print("[GPU] Cycles add-on not found; using CPU.", file=sys.stderr)
            return "CPU"

        cprefs = prefs.addons["cycles"].preferences

        # Platform-aware backend preference order
        order = []
        if preferred:
            order.append(preferred.upper())
        if sys.platform == "darwin":
            order += ["METAL"]
        else:
            order += ["CUDA", "OPTIX", "HIP", "ONEAPI", "OPENCL"]

        # Remove duplicates while preserving order
        seen = set()
        order = [b for b in order if not (b in seen or seen.add(b))]

        chosen = None
        for backend in order:
            try:
                cprefs.compute_device_type = backend
                cprefs.refresh_devices()
                any_used = False
                for device in cprefs.devices:
                    use_flag = backend in device.type or device.type in ("GPU", backend)
                    device.use = use_flag
                    any_used = any_used or use_flag

                if any_used:
                    bpy.context.scene.cycles.device = "GPU"
                    chosen = backend
                    break
            except (AttributeError, RuntimeError) as e:
                print(f"[GPU] Failed to configure {backend}: {e}", file=sys.stderr)
                continue

        if not chosen:
            print("[GPU] No supported GPU backend found; using CPU.", file=sys.stderr)
            bpy.context.scene.cycles.device = "CPU"
            return "CPU"

        print(f"[GPU] Using backend: {chosen}")
        return chosen

    def configure_render_settings(self) -> None:
        """Configure Blender render settings based on configuration."""
        scene = self.scene
        scene.render.engine = self.config.render_engine
        scene.render.resolution_x = self.config.resolution[0]
        scene.render.resolution_y = self.config.resolution[1]
        scene.render.resolution_percentage = 100

        # Enable color management
        try:
            scene.view_settings.view_transform = "Filmic"
            scene.view_settings.look = "None"
            scene.sequencer_colorspace_settings.name = "Rec.709"
        except (AttributeError, KeyError) as e:
            print(
                f"[COLOR] Using fallback color settings for older Blender version: {e}",
                file=sys.stderr,
            )

        # Configure Cycles settings
        if self.config.render_engine == "CYCLES":
            cycles = scene.cycles
            cycles.samples = 64  # Good balance of quality/speed

            # Enable adaptive sampling and denoising
            try:
                cycles.use_adaptive_sampling = True
                cycles.use_denoising = True
                cycles.use_persistent_data = True
            except AttributeError:
                pass  # Handle version differences

        # Enable required render passes
        view_layer = scene.view_layers[0]
        view_layer.use_pass_z = True
        view_layer.use_pass_normal = True
        view_layer.use_pass_object_index = True


class PalletGenerator(BaseGenerator):
    """Generator for single pallet synthetic datasets.

    Specializes in generating high-quality single pallet scenes with
    configurable lighting, camera positioning, and annotation generation.
    """

    def __init__(self, config: GenerationConfig):
        """Initialize pallet generator.

        Args:
            config: Generation configuration
        """
        super().__init__(config)
        self.pallet_objects = []
        self._find_pallet_objects()

    def _find_pallet_objects(self) -> list[Any]:
        """Find pallet objects in the current scene.

        Returns:
            List of pallet objects found in scene
        """
        pallet_keywords = ["pallet", "palet"]
        pallets = []

        for obj in bpy.data.objects:
            if obj.type == "MESH" and any(
                keyword in obj.name.lower() for keyword in pallet_keywords
            ):
                pallets.append(obj)

        self.pallet_objects = pallets
        print(f"Found {len(pallets)} pallet objects")
        return pallets

    def position_camera_for_side_face(self, camera_obj: Any, target_obj: Any) -> None:
        """Position camera to capture pallet side faces optimally.

        Args:
            camera_obj: Blender camera object
            target_obj: Target pallet object to focus on
        """
        if not target_obj:
            return

        # Get target center and bounds
        target_center = Vector(target_obj.location)

        # Calculate optimal camera distance based on object size
        bbox = target_obj.bound_box
        max_dim = max(
            abs(max(c[i] for c in bbox) - min(c[i] for c in bbox)) for i in range(3)
        )
        distance = max_dim * 2.5  # Good distance for full object visibility

        # Random positioning around target with preference for side faces
        angle_horizontal = random.uniform(0, 360)  # nosec B311
        angle_vertical = random.uniform(10, 45)  # nosec B311  # Slight downward angle

        # Convert to radians
        h_rad = math.radians(angle_horizontal)
        v_rad = math.radians(angle_vertical)

        # Calculate camera position
        cam_x = target_center.x + distance * math.cos(h_rad) * math.cos(v_rad)
        cam_y = target_center.y + distance * math.sin(h_rad) * math.cos(v_rad)
        cam_z = target_center.z + distance * math.sin(v_rad)

        # Ensure camera is above ground
        ground_z = self.config.camera_config.get("min_ground_height", 0.1)
        cam_z = max(cam_z, ground_z)

        camera_obj.location = Vector((cam_x, cam_y, cam_z))

        # Point camera at target
        look_direction = target_center - camera_obj.location
        camera_obj.rotation_euler = look_direction.to_track_quat("-Z", "Y").to_euler()

    def generate_dataset(self) -> dict[str, Any]:
        """Generate complete pallet dataset.

        Returns:
            Dictionary containing generation statistics and metadata
        """
        if not self.pallet_objects:
            raise ValueError("No pallet objects found in scene")

        # Setup rendering
        self.enable_gpu()
        self.configure_render_settings()

        # Get camera
        camera = bpy.context.scene.camera
        if not camera:
            raise ValueError("No camera found in scene")

        stats = {
            "images_generated": 0,
            "objects_detected": len(self.pallet_objects),
            "export_formats": self.config.export_formats,
            "resolution": self.config.resolution,
        }

        print(f"Starting generation of {self.config.num_images} images...")

        for frame_idx in range(self.config.num_images):
            # Position camera randomly for each frame
            target_pallet = random.choice(self.pallet_objects)  # nosec B311
            self.position_camera_for_side_face(camera, target_pallet)

            # Randomize lighting if enabled
            if self.config.lighting_config.get("randomize_per_frame", False):
                self._randomize_lighting()

            # Render frame
            output_path = os.path.join(
                self.config.output_dir, "images", f"frame_{frame_idx:06d}.png"
            )
            bpy.context.scene.render.filepath = output_path
            bpy.ops.render.render(write_still=True)

            stats["images_generated"] += 1

            if frame_idx % 10 == 0:
                print(f"Generated {frame_idx + 1}/{self.config.num_images} images")

        print(
            f"Dataset generation complete! Generated {stats['images_generated']} images"
        )
        return stats

    def _randomize_lighting(self) -> None:
        """Randomize scene lighting for realism."""
        # Remove existing generated lights
        existing_lights = [
            obj
            for obj in bpy.data.objects
            if obj.type == "LIGHT" and "Generated" in obj.name
        ]
        for light in existing_lights:
            bpy.data.objects.remove(light)

        # Add new random lights
        light_count = random.randint(
            *self.config.lighting_config["light_count_range"]
        )  # nosec B311

        for i in range(light_count):
            # Create light
            bpy.ops.object.light_add(type="POINT")
            light = bpy.context.active_object
            light.name = f"Generated_Light_{i}"

            # Random position around scene
            light.location = Vector(
                (
                    random.uniform(-5, 5),  # nosec B311
                    random.uniform(-5, 5),  # nosec B311
                    random.uniform(2, 6),  # nosec B311
                )
            )

            # Random energy
            light.data.energy = random.uniform(100, 1000)  # nosec B311

            # Random color if enabled
            if self.config.lighting_config.get(
                "use_colored_lights", False
            ) and random.random() < self.config.lighting_config.get(  # nosec B311
                "colored_light_probability", 0.5
            ):
                hue = random.random()  # nosec B311
                saturation = random.uniform(0.3, 0.8)  # nosec B311
                value = 1.0
                rgb = colorsys.hsv_to_rgb(hue, saturation, value)
                light.data.color = rgb + (1.0,)  # Add alpha


class WarehouseGenerator(BaseGenerator):
    """Generator for warehouse scene synthetic datasets.

    Specializes in generating complex warehouse environments with
    multiple pallets, realistic camera paths, and advanced scene management.
    """

    def __init__(self, config: GenerationConfig):
        """Initialize warehouse generator.

        Args:
            config: Generation configuration
        """
        super().__init__(config)
        self.warehouse_objects = self._analyze_warehouse_scene()

    def _analyze_warehouse_scene(self) -> dict[str, list[Any]]:
        """Analyze warehouse scene and categorize objects.

        Returns:
            Dictionary categorizing warehouse objects by type
        """
        scene_objects = {
            "pallets": [],
            "boxes": [],
            "racks": [],
            "warehouse_structure": [],
            "all_objects": list(bpy.data.objects),
        }

        keywords = {
            "pallets": ["pallet", "palet"],
            "boxes": ["box", "cube", "create"],
            "racks": ["rack", "mezanine", "shelf"],
            "warehouse_structure": [
                "hangar",
                "construction",
                "roof",
                "door",
                "wall",
                "floor",
            ],
        }

        for obj in bpy.data.objects:
            if obj.type != "MESH":
                continue

            obj_name_lower = obj.name.lower()
            for category, category_keywords in keywords.items():
                if any(keyword in obj_name_lower for keyword in category_keywords):
                    scene_objects[category].append(obj)
                    break

        # Log findings
        for category, objects in scene_objects.items():
            if category != "all_objects":
                print(f"Found {len(objects)} {category}")

        return scene_objects

    def generate_warehouse_path(
        self, num_points: int = 50
    ) -> list[tuple[Vector, Vector]]:
        """Generate realistic warehouse navigation path.

        Args:
            num_points: Number of path points to generate

        Returns:
            List of (position, rotation) tuples for camera path
        """
        if not self.warehouse_objects["pallets"]:
            # Generate simple linear path if no pallets
            return self._generate_simple_path(num_points)

        # Generate path based on pallet positions
        pallet_positions = [
            Vector(p.location) for p in self.warehouse_objects["pallets"]
        ]

        # Create path that visits multiple pallet areas
        path_points = []
        height_range = self.config.camera_config.get("height_range", (1.4, 2.0))

        for i in range(num_points):
            # Interpolate between pallet areas
            progress = i / (num_points - 1)

            # Select target pallet based on progress
            pallet_idx = int(progress * len(pallet_positions)) % len(pallet_positions)
            target_pos = pallet_positions[pallet_idx]

            # Add variation for realistic movement
            variation = self.config.camera_config.get("path_variation", 0.5)
            camera_pos = Vector(
                (
                    target_pos.x + random.uniform(-variation, variation),  # nosec B311
                    target_pos.y + random.uniform(-variation, variation),  # nosec B311
                    random.uniform(*height_range),  # nosec B311
                )
            )

            # Calculate rotation to look at target
            look_dir = (target_pos - camera_pos).normalized()
            rotation = look_dir.to_track_quat("-Z", "Y").to_euler()

            path_points.append((camera_pos, rotation))

        return path_points

    def _generate_simple_path(self, num_points: int) -> list[tuple[Vector, Vector]]:
        """Generate simple linear path when no specific targets available.

        Args:
            num_points: Number of path points to generate

        Returns:
            List of (position, rotation) tuples for camera path
        """
        path_points = []
        height_range = self.config.camera_config.get("height_range", (1.4, 2.0))

        for i in range(num_points):
            progress = i / (num_points - 1)

            camera_pos = Vector(
                (
                    progress * 10 - 5,  # -5 to 5 range
                    random.uniform(-2, 2),  # nosec B311  # Small Y variation
                    random.uniform(*height_range),  # nosec B311
                )
            )

            # Look forward with slight downward angle
            rotation = Euler((math.radians(-5), 0, 0))

            path_points.append((camera_pos, rotation))

        return path_points

    def generate_dataset(self) -> dict[str, Any]:
        """Generate complete warehouse dataset.

        Returns:
            Dictionary containing generation statistics and metadata
        """
        # Setup rendering
        self.enable_gpu()
        self.configure_render_settings()

        # Get camera
        camera = bpy.context.scene.camera
        if not camera:
            raise ValueError("No camera found in scene")

        # Generate camera path
        camera_path = self.generate_warehouse_path(self.config.num_images)

        stats = {
            "images_generated": 0,
            "pallets_found": len(self.warehouse_objects["pallets"]),
            "boxes_found": len(self.warehouse_objects["boxes"]),
            "export_formats": self.config.export_formats,
            "resolution": self.config.resolution,
        }

        print("Starting warehouse dataset generation...")
        print(f"Camera path with {len(camera_path)} points")

        for frame_idx, (camera_pos, camera_rot) in enumerate(camera_path):
            if frame_idx >= self.config.num_images:
                break

            # Position camera
            camera.location = camera_pos
            camera.rotation_euler = camera_rot

            # Randomize lighting if enabled
            if self.config.lighting_config.get("randomize_per_frame", False):
                self._randomize_lighting()

            # Render frame
            output_path = os.path.join(
                self.config.output_dir, "images", f"warehouse_{frame_idx:06d}.png"
            )
            bpy.context.scene.render.filepath = output_path
            bpy.ops.render.render(write_still=True)

            stats["images_generated"] += 1

            if frame_idx % 10 == 0:
                print(f"Generated {frame_idx + 1}/{self.config.num_images} images")

        print(
            f"Warehouse dataset generation complete! Generated {stats['images_generated']} images"
        )
        return stats

    def _randomize_lighting(self) -> None:
        """Randomize warehouse lighting for realism."""
        # Implementation similar to PalletGenerator but with warehouse-specific parameters
        existing_lights = [
            obj
            for obj in bpy.data.objects
            if obj.type == "LIGHT" and "Generated" in obj.name
        ]
        for light in existing_lights:
            bpy.data.objects.remove(light)

        light_count = random.randint(
            *self.config.lighting_config["light_count_range"]
        )  # nosec B311

        for i in range(light_count):
            # Create area lights for warehouse (more realistic)
            bpy.ops.object.light_add(type="AREA")
            light = bpy.context.active_object
            light.name = f"Generated_Warehouse_Light_{i}"

            # Position lights higher for warehouse scale
            light.location = Vector(
                (
                    random.uniform(-10, 10),  # nosec B311
                    random.uniform(-10, 10),  # nosec B311
                    random.uniform(4, 8),  # nosec B311
                )
            )

            # Higher energy for warehouse scale
            light.data.energy = random.uniform(500, 2000)  # nosec B311
            light.data.size = random.uniform(1, 3)  # nosec B311  # Area light size

            # Warehouse lighting is typically cooler
            if self.config.lighting_config.get(
                "use_colored_lights", False
            ) and random.random() < self.config.lighting_config.get(  # nosec B311
                "colored_light_probability", 0.3
            ):
                # Cooler color temperature for warehouse
                temperature = random.uniform(4000, 6500)  # nosec B311  # Kelvin
                # Convert temperature to RGB (simplified)
                rgb = (1.0, 0.95, 0.8) if temperature < 5000 else (0.9, 0.95, 1.0)
                light.data.color = rgb + (1.0,)
