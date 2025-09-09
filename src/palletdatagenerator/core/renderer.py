"""Blender rendering functionality for dataset generation."""

import os
import sys
from typing import Any, Callable

try:
    import bpy
    from mathutils import Vector

    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False

    class Vector:
        def __init__(self, *args):
            pass


class BlenderRenderer:
    """Professional Blender rendering interface for synthetic datasets.

    Handles all aspects of Blender rendering including compositor setup,
    multi-pass rendering, and output management.
    """

    def __init__(self, output_paths: dict[str, str]):
        """Initialize renderer with output paths.

        Args:
            output_paths: Dictionary mapping pass types to output directories

        Raises:
            RuntimeError: If Blender is not available
        """
        if not BLENDER_AVAILABLE:
            raise RuntimeError("Blender Python API not available")

        self.output_paths = output_paths
        self.scene = bpy.context.scene
        self._setup_compositor()

    def _setup_compositor(self) -> None:
        """Setup Blender compositor for multi-pass rendering."""
        self.scene.use_nodes = True
        node_tree = self.scene.node_tree
        node_tree.nodes.clear()

        # Render layers input
        render_layer = node_tree.nodes.new("CompositorNodeRLayers")

        # RGB output (default)
        # This is handled by the regular render output

        # Depth output (16-bit PNG)
        if "depth" in self.output_paths:
            depth_output = node_tree.nodes.new("CompositorNodeOutputFile")
            depth_output.base_path = self.output_paths["depth"]
            depth_output.file_slots[0].path = "depth_######"
            depth_output.format.file_format = "PNG"
            depth_output.format.color_depth = "16"
            depth_output.format.color_mode = "BW"

            # Convert depth to millimeters and normalize
            depth_multiply = node_tree.nodes.new("CompositorNodeMath")
            depth_multiply.operation = "MULTIPLY"
            depth_multiply.inputs[1].default_value = 1000.0  # Convert to mm

            depth_normalize = node_tree.nodes.new("CompositorNodeMath")
            depth_normalize.operation = "MULTIPLY"
            depth_normalize.inputs[1].default_value = 1.0 / 65535.0  # Normalize to 0-1

            depth_clamp = node_tree.nodes.new("CompositorNodeMath")
            depth_clamp.operation = "MINIMUM"
            depth_clamp.inputs[1].default_value = 1.0

            # Connect depth processing chain
            node_tree.links.new(render_layer.outputs["Depth"], depth_multiply.inputs[0])
            node_tree.links.new(depth_multiply.outputs[0], depth_normalize.inputs[0])
            node_tree.links.new(depth_normalize.outputs[0], depth_clamp.inputs[0])
            node_tree.links.new(depth_clamp.outputs[0], depth_output.inputs[0])

        # Normal output
        if "normals" in self.output_paths:
            normal_output = node_tree.nodes.new("CompositorNodeOutputFile")
            normal_output.base_path = self.output_paths["normals"]
            normal_output.file_slots[0].path = "normal_######"
            normal_output.format.file_format = "PNG"
            normal_output.format.color_depth = "8"
            normal_output.format.color_mode = "RGB"

            # Process normals (convert from -1,1 to 0,1 range)
            normal_separate = node_tree.nodes.new("CompositorNodeSepRGBA")
            normal_combine = node_tree.nodes.new("CompositorNodeCombRGBA")

            node_tree.links.new(
                render_layer.outputs["Normal"], normal_separate.inputs[0]
            )

            # Convert each channel from -1,1 to 0,1
            for i in range(3):
                add_node = node_tree.nodes.new("CompositorNodeMath")
                add_node.operation = "ADD"
                add_node.inputs[1].default_value = 1.0

                multiply_node = node_tree.nodes.new("CompositorNodeMath")
                multiply_node.operation = "MULTIPLY"
                multiply_node.inputs[1].default_value = 0.5

                node_tree.links.new(normal_separate.outputs[i], add_node.inputs[0])
                node_tree.links.new(add_node.outputs[0], multiply_node.inputs[0])
                node_tree.links.new(multiply_node.outputs[0], normal_combine.inputs[i])

            normal_combine.inputs[3].default_value = 1.0  # Alpha
            node_tree.links.new(normal_combine.outputs[0], normal_output.inputs[0])

        # Object index output
        if "index" in self.output_paths:
            index_output = node_tree.nodes.new("CompositorNodeOutputFile")
            index_output.base_path = self.output_paths["index"]
            index_output.file_slots[0].path = "index_######"
            index_output.format.file_format = "PNG"
            index_output.format.color_depth = "8"
            index_output.format.color_mode = "BW"

            node_tree.links.new(render_layer.outputs["IndexOB"], index_output.inputs[0])

    def configure_scene_for_rendering(
        self, resolution: tuple[int, int], engine: str = "CYCLES", samples: int = 64
    ) -> None:
        """Configure scene rendering settings.

        Args:
            resolution: Tuple of (width, height)
            engine: Render engine ('CYCLES' or 'EEVEE')
            samples: Number of samples for rendering quality
        """
        scene = self.scene

        # Basic render settings
        scene.render.engine = engine
        scene.render.resolution_x = resolution[0]
        scene.render.resolution_y = resolution[1]
        scene.render.resolution_percentage = 100

        # Color management for realism
        try:
            scene.view_settings.view_transform = "Filmic"
            scene.view_settings.look = "None"
            scene.sequencer_colorspace_settings.name = "Rec.709"
        except Exception:
            print("[Warning] Could not set color management settings")

        # Engine-specific settings
        if engine == "CYCLES":
            cycles = scene.cycles
            cycles.samples = samples

            # Performance optimizations
            try:
                cycles.use_adaptive_sampling = True
                cycles.use_denoising = True
                cycles.use_persistent_data = True  # Faster for multiple renders
                cycles.light_threshold = 0.001  # Reduce fireflies
            except AttributeError:
                print(
                    "[Warning] Some Cycles settings not available in this Blender version"
                )

        # Enable render passes
        view_layer = scene.view_layers[0]
        view_layer.use_pass_z = True
        view_layer.use_pass_normal = True
        view_layer.use_pass_object_index = True

    def render_frame(self, frame_number: int, output_name: str | None = None) -> str:
        """Render a single frame with all passes.

        Args:
            frame_number: Frame number for output naming
            output_name: Optional custom output name (defaults to frame number)

        Returns:
            Path to rendered RGB image
        """
        if output_name is None:
            output_name = f"frame_{frame_number:06d}"

        # Set frame for animation (if needed)
        self.scene.frame_set(frame_number)

        # Main RGB output path
        rgb_path = os.path.join(
            self.output_paths.get("images", "."), f"{output_name}.png"
        )
        self.scene.render.filepath = rgb_path

        # Render with all passes
        bpy.ops.render.render(write_still=True)

        return rgb_path

    def enable_gpu_rendering(self, preferred_backend: str | None = None) -> str:
        """Enable GPU rendering with optimal backend selection.

        Args:
            preferred_backend: Preferred GPU backend (optional)

        Returns:
            Selected backend name or 'CPU' if no GPU available
        """
        prefs = bpy.context.preferences
        if "cycles" not in prefs.addons:
            print("[GPU] Cycles add-on not found; using CPU.")
            return "CPU"

        cycles_prefs = prefs.addons["cycles"].preferences

        # Platform-aware backend selection
        backend_order = []
        if preferred_backend:
            backend_order.append(preferred_backend.upper())

        if sys.platform == "darwin":  # macOS
            backend_order.extend(["METAL"])
        else:  # Windows/Linux
            backend_order.extend(["CUDA", "OPTIX", "HIP", "ONEAPI", "OPENCL"])

        # Remove duplicates while preserving order
        seen = set()
        backend_order = [b for b in backend_order if not (b in seen or seen.add(b))]

        selected_backend = None
        for backend in backend_order:
            try:
                cycles_prefs.compute_device_type = backend
                cycles_prefs.refresh_devices()

                # Enable compatible devices
                any_device_enabled = False
                for device in cycles_prefs.devices:
                    if backend in device.type or device.type in ("GPU", backend):
                        device.use = True
                        any_device_enabled = True
                    else:
                        device.use = False

                if any_device_enabled:
                    bpy.context.scene.cycles.device = "GPU"
                    selected_backend = backend
                    break

            except Exception as e:
                print(f"[GPU] Failed to initialize {backend}: {e}")
                continue

        if not selected_backend:
            print("[GPU] No compatible GPU backend found; using CPU.")
            bpy.context.scene.cycles.device = "CPU"
            return "CPU"

        print(f"[GPU] Successfully enabled {selected_backend} rendering")
        return selected_backend

    def auto_select_denoiser(self, gpu_backend: str) -> str:
        """Automatically select optimal denoiser based on GPU backend.

        Args:
            gpu_backend: Currently active GPU backend

        Returns:
            Selected denoiser name
        """
        denoiser = "OPTIX" if gpu_backend in ("CUDA", "OPTIX") else "OPENIMAGEDENOISE"

        # Apply denoiser setting
        try:
            if hasattr(self.scene.cycles, "denoiser"):
                self.scene.cycles.denoiser = denoiser
            elif hasattr(self.scene.cycles, "use_denoising"):
                self.scene.cycles.use_denoising = True
        except Exception:
            print(f"[Warning] Could not set denoiser to {denoiser}")

        return denoiser

    def setup_object_indices(self, objects: list[Any]) -> dict[Any, int]:
        """Setup object indices for segmentation pass.

        Args:
            objects: List of objects to assign indices

        Returns:
            Dictionary mapping objects to their assigned indices
        """
        object_indices = {}

        for idx, obj in enumerate(objects, start=1):
            if hasattr(obj, "pass_index"):
                obj.pass_index = idx
                object_indices[obj] = idx
            else:
                print(f"[Warning] Object {obj.name} does not support pass_index")

        return object_indices

    def create_analysis_render(
        self, frame_number: int, objects_info: list[dict[str, Any]]
    ) -> str | None:
        """Create analysis render with bounding box overlays.

        Args:
            frame_number: Frame number for output naming
            objects_info: List of object information dictionaries

        Returns:
            Path to analysis image or None if failed
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("[Warning] PIL not available, skipping analysis render")
            return None

        # First, get the regular render
        rgb_path = self.render_frame(frame_number)

        if not os.path.exists(rgb_path):
            print(f"[Error] RGB render not found: {rgb_path}")
            return None

        # Load image for annotation
        try:
            img = Image.open(rgb_path)
            draw = ImageDraw.Draw(img)

            # Try to load a font
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except OSError:
                font = ImageFont.load_default()

            # Draw bounding boxes and labels
            colors = [
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
                (255, 255, 0),
                (255, 0, 255),
            ]

            for idx, obj_info in enumerate(objects_info):
                if "bbox_2d" not in obj_info:
                    continue

                bbox = obj_info["bbox_2d"]
                color = colors[idx % len(colors)]

                # Draw bounding box
                draw.rectangle(
                    [(bbox["x_min"], bbox["y_min"]), (bbox["x_max"], bbox["y_max"])],
                    outline=color,
                    width=2,
                )

                # Draw label
                label = obj_info.get("class_name", f"Object_{idx}")
                draw.text(
                    (bbox["x_min"], bbox["y_min"] - 25), label, fill=color, font=font
                )

            # Save analysis image
            analysis_path = os.path.join(
                self.output_paths.get("analysis", "."),
                f"analysis_{frame_number:06d}.png",
            )
            img.save(analysis_path)

            return analysis_path

        except Exception as e:
            print(f"[Error] Failed to create analysis render: {e}")
            return None

    def batch_render(
        self, frame_range: tuple[int, int], progress_callback: Callable | None = None
    ) -> list[str]:
        """Render multiple frames in batch.

        Args:
            frame_range: Tuple of (start_frame, end_frame)
            progress_callback: Optional callback for progress updates

        Returns:
            List of rendered image paths
        """
        start_frame, end_frame = frame_range
        rendered_paths = []

        total_frames = end_frame - start_frame + 1

        for frame_num in range(start_frame, end_frame + 1):
            try:
                rgb_path = self.render_frame(frame_num)
                rendered_paths.append(rgb_path)

                if progress_callback:
                    progress = (frame_num - start_frame + 1) / total_frames
                    progress_callback(progress, frame_num, rgb_path)

            except Exception as e:
                print(f"[Error] Failed to render frame {frame_num}: {e}")
                continue

        return rendered_paths

    def cleanup(self) -> None:
        """Clean up temporary objects and reset scene state."""
        # Remove generated lights
        generated_lights = [
            obj
            for obj in bpy.data.objects
            if obj.type == "LIGHT" and "Generated" in obj.name
        ]

        for light in generated_lights:
            bpy.data.objects.remove(light)

        # Reset compositor if needed
        if self.scene.use_nodes:
            self.scene.node_tree.nodes.clear()
            self.scene.use_nodes = False

        print("[Cleanup] Rendering cleanup completed")
