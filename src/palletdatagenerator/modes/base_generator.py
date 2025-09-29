"""
Base generator class that contains shared functionality for all generation modes.
Provides common methods for scene setup, rendering, and data export.
"""

# Blender imports with fallback
import colorsys
import contextlib
import ensurepip
import glob
import importlib
import math
import os
import random
import site
import subprocess
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view as w2cv
from mathutils import Vector

from ..utils import logger


def _pip_install(args):
    """
    Run `python -m pip …` inside the current interpreter.
    Adds ~/.local to sys.path so the fresh install is usable immediately.
    """
    try:
        import pip  # noqa: F401
    except ModuleNotFoundError:
        ensurepip.bootstrap()

    cmd = [sys.executable, "-m", "pip"] + args
    logger.debug("▶ " + " ".join(cmd))
    subprocess.check_call(cmd)

    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.append(user_site)
        site.addsitedir(user_site)
    importlib.invalidate_caches()


# ---------------------------- 1) Pillow -----------------------------
try:
    from PIL import Image, ImageDraw, ImageFont  # noqa: F401

    PIL_AVAILABLE = True
except ModuleNotFoundError:
    _pip_install(["install", "pillow>=10.0.0"])
    from PIL import Image, ImageDraw, ImageFont  # retry

    PIL_AVAILABLE = True

# ----------------------- 2) pascal_voc_writer -----------------------
try:
    from pascal_voc_writer import Writer as VocWriter
except ImportError:
    try:
        _pip_install(["install", "pascal_voc_writer"])
        from pascal_voc_writer import Writer as VocWriter  # retry
    except Exception:
        VocWriter = None

logger.info(f"Pillow available: {PIL_AVAILABLE}")


class BaseGenerator:
    """
    Base class for all generation modes with shared functionality.
    """

    def __init__(self, config):
        self.config = config
        self.paths = {}

    def setup_folders(self):
        """Create the output folder structure."""
        root = self.config["output_dir"]
        os.makedirs(root, exist_ok=True)

        self.paths = {
            "images": self._ensure_dir(os.path.join(root, "images")),
            "depth": self._ensure_dir(os.path.join(root, "depth")),
            "normals": self._ensure_dir(os.path.join(root, "normals")),
            "index": self._ensure_dir(os.path.join(root, "index")),
            "analysis": self._ensure_dir(os.path.join(root, "analysis")),
            "yolo": self._ensure_dir(os.path.join(root, "yolo_labels")),
            "voc": self._ensure_dir(os.path.join(root, "voc_xml")),
            "keypoints": self._ensure_dir(os.path.join(root, "keypoints_labels")),
            "debug_3d": self._ensure_dir(os.path.join(root, "debug_3d")),
            "debug_3d_images": self._ensure_dir(
                os.path.join(root, "debug_3d", "images")
            ),
            "debug_3d_coordinates": self._ensure_dir(
                os.path.join(root, "debug_3d", "coordinates")
            ),
            "debug_3d_figures": self._ensure_dir(
                os.path.join(root, "debug_3d", "figures")
            ),
            "face_2d_boxes": self._ensure_dir(os.path.join(root, "face_2d_boxes")),
            "face_3d_coordinates": self._ensure_dir(
                os.path.join(root, "face_3d_coordinates")
            ),
        }
        return self.paths

    def _ensure_dir(self, path):
        """Create directory if it doesn't exist."""
        os.makedirs(path, exist_ok=True)
        return path

    def configure_render(self):
        """Configure Blender render settings."""
        cfg = self.config
        sc = bpy.context.scene

        sc.render.engine = cfg["render_engine"]
        sc.render.resolution_x = cfg["resolution_x"]
        sc.render.resolution_y = cfg["resolution_y"]
        sc.render.resolution_percentage = 100

        # Color Management
        with contextlib.suppress(Exception):
            sc.view_settings.view_transform = "Filmic"
        with contextlib.suppress(Exception):
            sc.view_settings.look = cfg.get(
                "color_management_look", "Medium High Contrast"
            )
        with contextlib.suppress(Exception):
            sc.view_settings.exposure = float(cfg.get("initial_exposure_ev", 0.0))
            sc.view_settings.gamma = 1.0
            sc.display_settings.display_device = "sRGB"

        # Cycles settings
        cyc = sc.cycles
        cyc.samples = cfg["fast_samples"] if cfg.get("fast_mode", False) else 128

        if hasattr(cyc, "use_adaptive_sampling"):
            cyc.use_adaptive_sampling = bool(cfg.get("fast_adaptive_sampling", False))

        if cfg.get("fast_mode", False):
            if hasattr(cyc, "use_denoising"):
                cyc.use_denoising = True

            # Set denoiser
            den = cfg.get(
                "_resolved_denoiser", cfg.get("fast_denoiser", "OPENIMAGEDENOISE")
            )
            for candidate in (den, "OPENIMAGEDENOISE", "OPTIX", "NLM"):
                try:
                    cyc.denoiser = candidate
                    break
                except Exception:
                    continue

            if hasattr(cyc, "use_persistent_data"):
                cyc.use_persistent_data = bool(cfg.get("cycles_persistent_data", True))
        else:
            if hasattr(cyc, "use_persistent_data"):
                cyc.use_persistent_data = False

        # Reduce fireflies
        if hasattr(cyc, "light_threshold"):
            cyc.light_threshold = 0.001

        # Enable passes
        vl = sc.view_layers[0]
        vl.use_pass_z = True
        vl.use_pass_normal = True
        vl.use_pass_object_index = True

    def setup_compositor_nodes(self):
        """Setup compositor nodes for depth, normals, and index passes."""
        scene = bpy.context.scene
        scene.use_nodes = True
        nt = scene.node_tree
        nt.nodes.clear()
        rl = nt.nodes.new("CompositorNodeRLayers")

        # DEPTH (16-bit mm)
        depth_out = nt.nodes.new("CompositorNodeOutputFile")
        depth_out.base_path = self.paths["depth"]
        depth_out.file_slots[0].path = "depth_######"
        depth_out.format.file_format = "PNG"
        depth_out.format.color_depth = "16"
        depth_out.format.color_mode = "BW"

        to_mm = nt.nodes.new("CompositorNodeMath")
        to_mm.operation = "MULTIPLY"
        to_mm.inputs[1].default_value = 1000.0
        mm_to_norm = nt.nodes.new("CompositorNodeMath")
        mm_to_norm.operation = "MULTIPLY"
        mm_to_norm.inputs[1].default_value = 1.0 / 65535.0
        clamp1 = nt.nodes.new("CompositorNodeMath")
        clamp1.operation = "MINIMUM"
        clamp1.inputs[1].default_value = 1.0

        nt.links.new(rl.outputs["Depth"], to_mm.inputs[0])
        nt.links.new(to_mm.outputs[0], mm_to_norm.inputs[0])
        nt.links.new(mm_to_norm.outputs[0], clamp1.inputs[0])
        nt.links.new(clamp1.outputs[0], depth_out.inputs[0])

        # NORMALS
        norm_out = nt.nodes.new("CompositorNodeOutputFile")
        norm_out.base_path = self.paths["normals"]
        norm_out.file_slots[0].path = "normal_######"
        norm_out.format.file_format = "PNG"
        norm_out.format.color_depth = "8"
        norm_out.format.color_mode = "RGB"

        sep = nt.nodes.new("CompositorNodeSepRGBA")
        combine = nt.nodes.new("CompositorNodeCombRGBA")
        nt.links.new(rl.outputs["Normal"], sep.inputs[0])
        for i in range(3):
            add1 = nt.nodes.new("CompositorNodeMath")
            add1.operation = "ADD"
            add1.inputs[1].default_value = 1.0
            mul1 = nt.nodes.new("CompositorNodeMath")
            mul1.operation = "MULTIPLY"
            mul1.inputs[1].default_value = 0.5
            nt.links.new(sep.outputs[i], add1.inputs[0])
            nt.links.new(add1.outputs[0], mul1.inputs[0])
            nt.links.new(mul1.outputs[0], combine.inputs[i])
        combine.inputs[3].default_value = 1.0
        nt.links.new(combine.outputs[0], norm_out.inputs[0])

        # INDEX
        idx_out = nt.nodes.new("CompositorNodeOutputFile")
        idx_out.base_path = self.paths["index"]
        idx_out.file_slots[0].path = "index_######"
        idx_out.format.file_format = "PNG"
        idx_out.format.color_depth = "8"
        idx_out.format.color_mode = "BW"
        nt.links.new(rl.outputs["IndexOB"], idx_out.inputs[0])

    def setup_environment(self):
        """Setup world background and floor."""
        # World/background
        self.setup_random_background()

        # Floor
        if self.config.get("add_floor", False):
            self.create_floor_plane()

    def setup_random_background(self):
        """Setup world background exactly as in original."""
        cfg = self.config
        cfg["_real_bg_selected"] = False
        world = bpy.context.scene.world
        if not world.use_nodes:
            world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputWorld")

        # Try real background images first
        if cfg.get("use_real_background", False):
            folder = cfg.get("real_background_images_dir")
            files = []
            if folder and os.path.isdir(folder):
                for ext in ("*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff"):
                    files += glob.glob(os.path.join(folder, ext))
            if files:
                bg = nodes.new("ShaderNodeBackground")
                img_node = nodes.new("ShaderNodeTexImage")
                img_node.image = bpy.data.images.load(random.choice(files))
                bg.inputs["Strength"].default_value = max(
                    cfg.get("world_min_strength", 0.2), 0.2
                )
                links.new(img_node.outputs["Color"], bg.inputs["Color"])
                links.new(bg.outputs["Background"], output.inputs["Surface"])
                cfg["_real_bg_selected"] = True
                return

        # Otherwise use random solid/gradient
        if not cfg.get("randomize_background", False):
            # Solid, dim but safe
            bg = nodes.new("ShaderNodeBackground")
            bg.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1.0)
            bg.inputs["Strength"].default_value = max(
                cfg.get("world_min_strength", 0.2), 0.2
            )
            links.new(bg.outputs["Background"], output.inputs["Surface"])
            return

        bg_type = random.choice(cfg["background_types"])
        if bg_type == "solid":
            bg = nodes.new("ShaderNodeBackground")
            bg.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1.0)
            bg.inputs["Strength"].default_value = max(
                cfg.get("world_min_strength", 0.2), 0.2
            )
            links.new(bg.outputs["Background"], output.inputs["Surface"])
        else:
            tex_coord = nodes.new("ShaderNodeTexCoord")
            mapping = nodes.new("ShaderNodeMapping")
            gradient = nodes.new("ShaderNodeTexGradient")
            ramp = nodes.new("ShaderNodeValToRGB")
            bg = nodes.new("ShaderNodeBackground")
            ramp.color_ramp.elements[0].color = (0.08, 0.08, 0.12, 1.0)
            ramp.color_ramp.elements[1].color = (0.3, 0.35, 0.45, 1.0)
            bg.inputs["Strength"].default_value = max(
                cfg.get("world_min_strength", 0.2), 0.2
            )
            links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
            links.new(mapping.outputs["Vector"], gradient.inputs["Vector"])
            links.new(gradient.outputs["Fac"], ramp.inputs["Fac"])
            links.new(ramp.outputs["Color"], bg.inputs["Color"])
            links.new(bg.outputs["Background"], output.inputs["Surface"])

    def create_floor_plane(self):
        """Create floor plane exactly as in original."""
        # Remove existing floor
        for obj in bpy.data.objects:
            if obj.name.startswith("SynthFloor"):
                bpy.data.objects.remove(obj, do_unlink=True)

        bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -1))
        floor = bpy.context.active_object
        floor.name = "SynthFloor"

        mat = bpy.data.materials.new("SynthFloorMat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        nodes.clear()

        principled = nodes.new("ShaderNodeBsdfPrincipled")
        output = nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])

        principled.inputs["Base Color"].default_value = (0.22, 0.22, 0.22, 1.0)

        # Set specular (compatible with different Blender versions)
        if not self._set_principled_input(
            principled, ["Specular", "Specular IOR Level"], 0.05
        ):
            logger.warning("[floor] Specular socket not found; skipping.")

        principled.inputs["Roughness"].default_value = 0.85
        floor.data.materials.append(mat)
        return floor

    def _set_principled_input(self, principled, candidates, value):
        """Set a Principled BSDF input using a list of possible socket names."""
        try:
            inputs = principled.inputs
            for name in candidates:
                if name in inputs:
                    inputs[name].default_value = value
                    return True
        except Exception:
            pass
        return False

    def randomize_object_material(self, obj):
        """Randomize object materials if enabled."""
        if not self.config.get("randomize_materials", False):
            return

        for slot in obj.material_slots:
            if slot.material and slot.material.use_nodes:
                nodes = slot.material.node_tree.nodes
                principled = next(
                    (n for n in nodes if n.type == "BSDF_PRINCIPLED"), None
                )
                if not principled:
                    continue

                base_color = principled.inputs["Base Color"]
                if not base_color.is_linked:
                    r, g, b, _ = base_color.default_value
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    h = (h + random.uniform(-0.3, 0.3)) % 1.0
                    s = max(0, min(1, s * random.uniform(0.5, 1.5)))
                    v = max(0, min(1, v * random.uniform(0.7, 1.3)))
                    nr, ng, nb = colorsys.hsv_to_rgb(h, s, v)
                    base_color.default_value = (nr, ng, nb, 1.0)

                if "Roughness" in principled.inputs:
                    principled.inputs["Roughness"].default_value = random.uniform(
                        0.1, 0.9
                    )
                if "Metallic" in principled.inputs:
                    principled.inputs["Metallic"].default_value = random.uniform(
                        0.0, 0.3
                    )

    # Analysis image generation functions
    def _text_wh(self, draw, text, font):
        """Get text width and height for different PIL versions."""
        if hasattr(draw, "textbbox"):
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            return right - left, bottom - top
        if hasattr(font, "getbbox"):
            left, top, right, bottom = font.getbbox(text)
            return right - left, bottom - top
        if hasattr(font, "getsize"):
            return font.getsize(text)
        return (len(text) * 6, 11)

    def draw_3d_bbox_edges(self, draw, corners_2d, color, width=2):
        """Draw 3D bounding box wireframe."""
        if not corners_2d or len(corners_2d) != 8:
            return
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),  # bottom face
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),  # top face
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),  # vertical edges
        ]
        for e in edges:
            p1, p2 = corners_2d[e[0]], corners_2d[e[1]]
            if p1[2] > 0 and p2[2] > 0:
                draw.line([p1[0], p1[1], p2[0], p2[1]], fill=color, width=width)

    def project_points_accurate(self, points, cam, sc):
        """Project 3D points to 2D screen coordinates."""
        res_x = sc.render.resolution_x
        res_y = sc.render.resolution_y
        out = []
        for p in points:
            v = Vector(p) if isinstance(p, list | tuple) else p
            co = w2cv(sc, cam, v)
            out.append(
                [co.x * res_x, (1.0 - co.y) * res_y, co.z]
                if co is not None and co.z > 0
                else [0, 0, -1]
            )
        return out

    def _draw_number(self, draw, xy, n, color, font, radius=6):
        """Draw numbered circle for 3D bbox corners."""
        x, y = xy
        r = radius
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
        txt_col = (255, 255, 255) if sum(color) < 300 else (0, 0, 0)
        w_txt, h_txt = self._text_wh(draw, str(n), font)
        draw.text((x - w_txt // 2, y - h_txt // 2), str(n), fill=txt_col, font=font)

    def create_analysis_image_multi(
        self,
        rgb_path,
        bboxes2d,
        bboxes3d,
        all_pockets_world,
        cam_obj,
        sc,
        output_path,
        frame_id,
        keypoints_data=None,
    ):
        """
        Create analysis image with 2D/3D bounding boxes, holes, and legend.
        Exact copy from original one_pallet_generator.py
        """

        if not PIL_AVAILABLE:
            return False
        try:
            # Import bpy_extras for 3D to 2D projection
            import os

            import bpy_extras.object_utils

            if not os.path.exists(rgb_path):
                return False

            img = Image.open(rgb_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            font_size = max(16, min(32, img.width // 40))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

            # Simple color scheme with normal colors
            color_2d = (0, 255, 0)  # Green for 2D bounding boxes
            color_3d = (255, 0, 0)  # Red for 3D bounding boxes
            color_hole = (0, 0, 255)  # Blue for holes
            color_keypoint_hidden = (128, 128, 128)  # Gray for hidden keypoints
            color_text = (255, 255, 255)  # White text

            # Draw all labels only if enabled
            if self.config.get("analysis_show_all_labels", True):
                # Draw 2D bounding boxes
                for b2d in bboxes2d:
                    draw.rectangle(
                        [b2d["x_min"], b2d["y_min"], b2d["x_max"], b2d["y_max"]],
                        outline=color_2d,
                        width=3,
                    )

                # Draw 3D bounding boxes
                for b3d in bboxes3d:
                    corners = self.project_points_accurate(
                        [Vector(c) for c in b3d["corners"]], cam_obj, sc
                    )
                    self.draw_3d_bbox_edges(draw, corners, color_3d, 2)
                    for idx, pt in enumerate(corners, start=1):
                        if pt[2] > 0:
                            self._draw_number(
                                draw, (int(pt[0]), int(pt[1])), idx, color_3d, font
                            )

                # Draw hole polygons
                for pockets_world in all_pockets_world:
                    for pk in pockets_world:
                        proj = self.project_points_accurate(pk, cam_obj, sc)
                        vis = [p for p in proj if p[2] > 0]
                        if len(vis) < 4:
                            continue
                        poly_xy = [(p[0], p[1]) for p in vis]
                        draw.polygon(poly_xy, outline=color_hole, width=2)

            # Draw keypoints if available and keypoints are enabled
            if keypoints_data and self.config.get("analysis_show_keypoints", True):
                # Simple face colors
                face_colors = [
                    (255, 0, 0),  # Red for face 0
                    (0, 255, 0),  # Green for face 1
                    (0, 0, 255),  # Blue for face 2
                    (255, 255, 0),  # Yellow for face 3
                ]

                # First pass: collect all keypoints and detect overlaps
                all_keypoints = []
                for face_idx, face_data in enumerate(keypoints_data):
                    keypoints = face_data["keypoints"]
                    face_color = face_colors[face_idx % len(face_colors)]
                    face_name = face_data.get("face_name", f"face_{face_idx}")

                    for kp in keypoints:
                        all_keypoints.append(
                            {
                                "kp": kp,
                                "face_idx": face_idx,
                                "face_color": face_color,
                                "face_name": face_name,
                            }
                        )

                # Detect overlapping keypoints (within 10 pixels)
                overlap_groups = self.detect_overlapping_keypoints(
                    all_keypoints, keypoints_data, threshold=10
                )

                # Second pass: draw keypoints, handling overlaps specially
                for face_idx, face_data in enumerate(keypoints_data):
                    keypoints = face_data["keypoints"]
                    face_color = face_colors[face_idx % len(face_colors)]
                    face_name = face_data.get("face_name", f"face_{face_idx}")

                    # Debug: Print face information (commented out for production)
                    # print(f"Face {face_idx} ({face_name}): {len(keypoints)} keypoints, color: {face_color}")

                    for kp in keypoints:
                        # Always draw all keypoints (visible and invisible)
                        x, y = int(kp["position_2d"][0]), int(kp["position_2d"][1])

                        # Only draw if we have valid coordinates
                        if x > 0 and y > 0:
                            # Check if this keypoint is part of an overlap group
                            is_overlap = False
                            overlap_group = None
                            for group in overlap_groups:
                                for group_kp in group:
                                    if (
                                        group_kp["kp"]["id"] == kp["id"]
                                        and group_kp["face_idx"] == face_idx
                                    ):
                                        is_overlap = True
                                        overlap_group = group
                                        break
                                if is_overlap:
                                    break

                            if kp["visible"]:
                                # Draw visible keypoint with face color
                                if is_overlap:
                                    # For overlapping keypoints, draw both colors (one inside the other)
                                    self.draw_overlapping_keypoint_circles(
                                        draw, overlap_group, x, y
                                    )
                                else:
                                    # Single keypoint
                                    radius = 4
                                    draw.ellipse(
                                        [
                                            x - radius,
                                            y - radius,
                                            x + radius,
                                            y + radius,
                                        ],
                                        fill=face_color,
                                        outline=(0, 0, 0),
                                        width=1,
                                    )

                                # Draw keypoint labels only if enabled
                                if self.config.get("keypoints_show_labels", True):
                                    # For overlapping keypoints, stack labels vertically
                                    if is_overlap:
                                        self.draw_overlapping_keypoint_labels(
                                            draw, font, overlap_group, x, y, radius
                                        )
                                    else:
                                        # Draw single keypoint labels
                                        self.draw_single_keypoint_labels(
                                            draw, font, kp, x, y, radius, color_text
                                        )
                            else:
                                # Draw invisible keypoint as gray circle with X
                                radius = 5 if is_overlap else 3
                                draw.ellipse(
                                    [x - radius, y - radius, x + radius, y + radius],
                                    fill=color_keypoint_hidden,
                                    outline=(0, 0, 0),
                                    width=2 if is_overlap else 1,
                                )
                                # Draw X mark
                                draw.line(
                                    [x - radius, y - radius, x + radius, y + radius],
                                    fill=(0, 0, 0),
                                    width=2 if is_overlap else 1,
                                )
                                draw.line(
                                    [x - radius, y + radius, x + radius, y - radius],
                                    fill=(0, 0, 0),
                                    width=2 if is_overlap else 1,
                                )

            # Draw 2D boxes for selected faces if enabled
            if self.config.get("analysis_show_2d_boxes", False) and keypoints_data:
                # Use different colors for each face
                face_colors_2d = [
                    (255, 0, 0),  # Red for face 0
                    (0, 255, 0),  # Green for face 1
                    (0, 0, 255),  # Blue for face 2
                    (255, 255, 0),  # Yellow for face 3
                ]

                for face_idx, face_data in enumerate(keypoints_data):
                    bbox_2d = face_data["bbox_2d"]
                    face_color = face_colors_2d[face_idx % len(face_colors_2d)]

                    # Draw 2D bounding box
                    draw.rectangle(
                        [
                            bbox_2d["x_min"],
                            bbox_2d["y_min"],
                            bbox_2d["x_max"],
                            bbox_2d["y_max"],
                        ],
                        outline=face_color,
                        width=2,
                    )

            # Draw 3D coordinates for selected faces if enabled
            if (
                self.config.get("analysis_show_3d_coordinates", False)
                and keypoints_data
            ):
                # Simple 3D face colors
                face_colors_3d = [
                    (255, 0, 255),  # Magenta for face 0
                    (0, 255, 255),  # Cyan for face 1
                    (255, 0, 0),  # Red for face 2
                    (0, 255, 0),  # Green for face 3
                ]

                for face_idx, face_data in enumerate(keypoints_data):
                    # Get the face corners (not the full 3D bounding box)
                    face_corners_3d = face_data.get("face_corners_3d", [])
                    if not face_corners_3d or len(face_corners_3d) != 4:
                        continue

                    # Use different color for each face
                    face_color = face_colors_3d[face_idx % len(face_colors_3d)]

                    # Project the 4 face corners to 2D
                    corners_2d = []
                    for corner_3d in face_corners_3d:
                        co_2d = bpy_extras.object_utils.world_to_camera_view(
                            sc, cam_obj, corner_3d
                        )
                        if 0 <= co_2d.x <= 1 and 0 <= co_2d.y <= 1:
                            x = int(co_2d.x * img.width)
                            y = int((1 - co_2d.y) * img.height)
                            corners_2d.append((x, y))

                    # Draw the face as a polygon (4 corners)
                    if len(corners_2d) == 4:
                        # Draw the face outline
                        draw.polygon(corners_2d, outline=face_color, width=3)

                        # Draw corner points for reference
                        for x, y in corners_2d:
                            draw.ellipse(
                                [x - 3, y - 3, x + 3, y + 3],
                                fill=face_color,
                                outline=(0, 0, 0),
                                width=1,
                            )

            # Draw legend - only show items that are actually displayed
            pad, sample_sz, line_gap = 8, 18, 8
            legend_items = [(f"Frame {frame_id}", None)]

            # Only add labels if they are actually shown
            if self.config.get("analysis_show_all_labels", True):
                if bboxes2d:
                    legend_items.append(("2D bbox", color_2d))
                if bboxes3d:
                    legend_items.append(("3D bbox", color_3d))
                if all_pockets_world:
                    legend_items.append(("Hole polygon", color_hole))

            # Add keypoints to legend if available and shown
            if keypoints_data and self.config.get("analysis_show_keypoints", True):
                # Add face colors for each selected face
                for face_idx, face_data in enumerate(keypoints_data):
                    face_color = face_colors[face_idx % len(face_colors)]
                    face_name = face_data.get("face_name", f"face_{face_idx}")
                    legend_items.append((f"Face: {face_name}", face_color))

            # Add 2D boxes to legend if shown
            if self.config.get("analysis_show_2d_boxes", False) and keypoints_data:
                # Add each face with its 2D box color
                face_colors_2d = [
                    (255, 0, 0),  # Red for face 0
                    (0, 255, 0),  # Green for face 1
                    (0, 0, 255),  # Blue for face 2
                    (255, 255, 0),  # Yellow for face 3
                ]
                for face_idx, face_data in enumerate(keypoints_data):
                    face_color = face_colors_2d[face_idx % len(face_colors_2d)]
                    face_name = face_data.get("face_name", f"face_{face_idx}")
                    legend_items.append((f"2D Box: {face_name}", face_color))

            # Add 3D coordinates to legend if shown
            if (
                self.config.get("analysis_show_3d_coordinates", False)
                and keypoints_data
            ):
                # Add each selected face with its color
                face_colors_3d = [
                    (255, 0, 255),  # Magenta for face 0
                    (0, 255, 255),  # Cyan for face 1
                    (255, 0, 0),  # Red for face 2
                    (0, 255, 0),  # Green for face 3
                ]
                for face_idx, face_data in enumerate(keypoints_data):
                    face_color = face_colors_3d[face_idx % len(face_colors_3d)]
                    face_name = face_data.get("face_name", f"face_{face_idx}")
                    legend_items.append((f"3D Face: {face_name}", face_color))
            dims = [self._text_wh(draw, t, font) for t, _ in legend_items]
            legend_w = (
                max(
                    w + (sample_sz + 6 if c else 0)
                    for (w, _), (_, c) in zip(dims, legend_items, strict=False)
                )
                + 2 * pad
            )
            legend_h = sum(h for _, h in dims) + (len(dims) - 1) * line_gap + 2 * pad
            lx, ly = img.width - legend_w - 10, 10
            draw.rectangle([lx, ly, lx + legend_w, ly + legend_h], fill=(0, 0, 0, 180))
            y = ly + pad
            for (text, col), (_tw, th) in zip(legend_items, dims, strict=False):
                if col:
                    swx = lx + pad
                    swy = y + (th - sample_sz) // 2
                    draw.rectangle(
                        [swx, swy, swx + sample_sz, swy + sample_sz], fill=col
                    )
                    tx = swx + sample_sz + 6
                else:
                    tx = lx + pad
                draw.text((tx, y), text, fill=color_text, font=font)
                y += th + line_gap

            img.save(output_path, "PNG", quality=95)
            logger.debug(f"Analysis image saved successfully to: {output_path}")

            # Verify the file was actually created
            import os

            if os.path.exists(output_path):
                _file_size = os.path.getsize(output_path)

            else:
                return False

            return True
        except Exception as e:
            logger.error(f"Analysis overlay error: {e}")
            import traceback

            traceback.print_exc()
            return False

    # Additional methods will be added as needed...

    def _get_ground_z(self):
        """Get the Z coordinate of the ground/floor."""
        floor = bpy.data.objects.get("SynthFloor")
        if floor:
            return float(floor.location.z)
        return float(self.config.get("assumed_ground_z", -1.0))

    def _random_light_color(self):
        """Generate a random light color based on configuration."""
        cfg = self.config
        if not cfg.get("use_colored_lights", True):
            return (1.0, 1.0, 1.0)
        if random.random() > cfg.get("colored_light_probability", 0.6):
            return (1.0, 1.0, 1.0)
        palette = cfg.get("light_color_palette", [])
        if palette:
            r, g, b, _ = random.choice(palette)
            return (r, g, b)
        h = random.random()
        s = random.uniform(0.2, 0.8)
        v = random.uniform(0.7, 1.0)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (r, g, b)

    def _aim_at(self, obj, target_loc):
        """Rotate obj so -Z axis points to target (like a camera)."""
        look_dir = (target_loc - obj.location).normalized()
        obj.rotation_euler = look_dir.to_track_quat("-Z", "Y").to_euler()

    def _place_light_around(self, anchor_obj):
        """Place a light around the anchor object."""
        cfg = self.config
        dist = random.uniform(*cfg.get("light_distance_range", (2.0, 6.0)))
        az_deg = random.uniform(0, 360)
        el_deg = random.uniform(*cfg.get("light_elevation_deg_range", (10.0, 80.0)))
        az = math.radians(az_deg)
        el = math.radians(el_deg)
        anchor = Vector(anchor_obj.location)
        pos = anchor + Vector(
            (
                dist * math.cos(az) * math.cos(el),
                dist * math.sin(az) * math.cos(el),
                dist * math.sin(el),
            )
        )
        ground_z = self._get_ground_z()
        if pos.z < ground_z + 0.05:
            pos.z = ground_z + 0.05
        return pos, el_deg, az_deg, dist

    def create_random_lights(self, anchor_obj, replace_existing=False):
        """
        Create 1..N random lights around anchor_obj.
        Also ensures at least one neutral 'key' light when requested.
        EXACT implementation from original one_pallet_generator.py
        """
        cfg = self.config

        if replace_existing:
            for o in [
                o
                for o in bpy.data.objects
                if o.type == "LIGHT" and o.name.startswith("SynthLight_")
            ]:
                bpy.data.objects.remove(o, do_unlink=True)

        n = random.randint(*cfg.get("light_count_range", (1, 3)))
        types = cfg.get("light_types", ["POINT", "AREA", "SPOT", "SUN"])
        energy_ranges = cfg.get(
            "light_energy_ranges",
            {
                "POINT": (50, 300),
                "AREA": (30, 200),
                "SPOT": (300, 1200),
                "SUN": (2, 8),
            },
        )

        created = []
        brightest_energy = 0.0

        for i in range(n):
            lt = random.choice(types)
            L = bpy.data.lights.new(f"SynthLightData_{lt}_{i}", lt)
            er = energy_ranges.get(lt, (50, 300))
            L.energy = random.uniform(*er)
            if lt == "AREA":
                L.size = random.uniform(0.5, 3.0)
            if lt == "SPOT":
                L.spot_size = math.radians(
                    random.uniform(*cfg.get("spot_size_deg_range", (20.0, 50.0)))
                )
                L.spot_blend = random.uniform(*cfg.get("spot_blend_range", (0.1, 0.4)))
            L.color = self._random_light_color()

            Lo = bpy.data.objects.new(f"SynthLight_{lt}_{i}", L)
            bpy.context.collection.objects.link(Lo)

            loc, _, _, _ = self._place_light_around(anchor_obj)
            Lo.location = loc
            self._aim_at(Lo, Vector(anchor_obj.location))
            created.append(Lo)
            brightest_energy = max(brightest_energy, L.energy)

        # Ensure a key light for realism (white, decent energy)
        if cfg.get("force_key_light", True):
            need_key = True
            for o in created:
                if hasattr(o.data, "color"):
                    r, g, b = o.data.color
                    is_whiteish = (abs(r - 1.0) + abs(g - 1.0) + abs(b - 1.0)) < 0.3
                    if is_whiteish and o.data.energy >= cfg.get(
                        "min_key_light_energy", 500.0
                    ):
                        need_key = False
                        break
            if need_key:
                lt = (
                    "AREA"
                    if "AREA" in types
                    else ("SPOT" if "SPOT" in types else "POINT")
                )
                L = bpy.data.lights.new("SynthLightData_KEY", lt)
                if lt == "AREA":
                    L.size = 2.0
                if lt == "SPOT":
                    L.spot_size = math.radians(35.0)
                    L.spot_blend = 0.2
                L.color = (1.0, 1.0, 1.0)
                L.energy = max(
                    cfg.get("min_key_light_energy", 500.0), brightest_energy * 1.2
                )
                Lo = bpy.data.objects.new("SynthLight_KEY", L)
                bpy.context.collection.objects.link(Lo)
                loc, _, _, _ = self._place_light_around(anchor_obj)
                Lo.location = loc
                self._aim_at(Lo, Vector(anchor_obj.location))
                created.append(Lo)
                logger.debug(f"Created key light with energy {L.energy}")

        # Ensure minimum total lighting energy
        total_energy = sum(light.data.energy for light in created)
        min_total_energy = cfg.get("min_total_light_energy", 300.0)

        if total_energy < min_total_energy:
            # Add an additional fill light to boost overall brightness
            fill_energy = min_total_energy - total_energy + 100  # Extra 100 for safety
            L_fill = bpy.data.lights.new("SynthLightData_FILL", "AREA")
            L_fill.energy = fill_energy
            L_fill.color = (1.0, 1.0, 1.0)
            L_fill.size = 3.0

            Lo_fill = bpy.data.objects.new("SynthLight_FILL", L_fill)
            bpy.context.collection.objects.link(Lo_fill)

            # Position fill light from a different angle
            loc, _, _, _ = self._place_light_around(anchor_obj)
            loc.x += random.uniform(-2, 2)  # Offset position
            loc.y += random.uniform(-2, 2)
            Lo_fill.location = loc
            self._aim_at(Lo_fill, Vector(anchor_obj.location))
            created.append(Lo_fill)

        return created

    def get_bbox_2d_accurate(self, obj, cam, sc):
        """Get accurate 2D bounding box - EXACT from original."""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh_eval = obj_eval.to_mesh()
        verts_world = [obj_eval.matrix_world @ v.co for v in mesh_eval.vertices]
        obj_eval.to_mesh_clear()
        if not verts_world:
            return None
        proj = self.project_points(verts_world, cam, sc)
        valid = [p for p in proj if p[2] > 0]
        if not valid:
            return None
        xs, ys = zip(*[(p[0], p[1]) for p in valid], strict=False)
        res_x, res_y = sc.render.resolution_x, sc.render.resolution_y
        x_min_full, y_min_full = min(xs), min(ys)
        x_max_full, y_max_full = max(xs), max(ys)
        x0, y0 = max(0, x_min_full), max(0, y_min_full)
        x1, y1 = min(res_x, x_max_full), min(res_y, y_max_full)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            return None
        full_w = x_max_full - x_min_full
        full_h = y_max_full - y_min_full
        full_area = max(0.0, full_w * full_h)
        vis_area = w * h
        vis_ratio = vis_area / full_area if full_area > 0 else 0
        crop_ratio = 1.0 - vis_ratio
        return {
            "x_min": x0,
            "y_min": y0,
            "x_max": x1,
            "y_max": y1,
            "width": w,
            "height": h,
            "center": [(x0 + x1) / 2, (y0 + y1) / 2],
            "area": vis_area,
            "full_bbox": {
                "x_min": x_min_full,
                "y_min": y_min_full,
                "x_max": x_max_full,
                "y_max": y_max_full,
                "width": full_w,
                "height": full_h,
                "area": full_area,
            },
            "visible_ratio": vis_ratio,
            "crop_ratio": crop_ratio,
            "is_cropped": crop_ratio > 0.01,
        }

    def bbox_3d_oriented(self, obj):
        """Get 3D oriented bounding box - EXACT from original."""
        bpy.context.view_layer.update()
        world = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        cen = sum(world, Vector()) / 8
        size = list(obj.dimensions)
        return {
            "corners": [[v.x, v.y, v.z] for v in world],
            "center": [cen.x, cen.y, cen.z],
            "size": size,
        }

    def project_points(self, points, cam, sc):
        """Project 3D points to 2D screen coordinates - EXACT from original."""
        res_x, res_y = sc.render.resolution_x, sc.render.resolution_y
        out = []
        for p in points:
            co = w2cv(sc, cam, Vector(p))
            if co and co.z > 0:
                out.append([co.x * res_x, (1 - co.y) * res_y, co.z])
            else:
                out.append([0, 0, -1])
        return out

    def hole_bboxes_3d(self, obj, side_margin=0.08, _gap=0.15, hole_height=(0.2, 0.85)):
        """Generate 3D hole/pocket bounding boxes for pallet - EXACT from original."""
        bb = obj.bound_box
        xs, ys, zs = zip(*bb, strict=False)
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        zmin, zmax = min(zs), max(zs)
        w = xmax - xmin
        d = ymax - ymin
        h = zmax - zmin
        z0 = zmin + h * hole_height[0]
        z1 = zmin + h * hole_height[1]

        pockets = []
        hole_frac = 0.35
        x_start = xmin + w * side_margin
        x_end = xmax - w * side_margin
        hole_w = (x_end - x_start) * hole_frac

        # front/back (two each)
        pockets += [
            [
                [x_start, ymax, z0],
                [x_start + hole_w, ymax, z0],
                [x_start + hole_w, ymax, z1],
                [x_start, ymax, z1],
            ],
            [
                [x_end - hole_w, ymax, z0],
                [x_end, ymax, z0],
                [x_end, ymax, z1],
                [x_end - hole_w, ymax, z1],
            ],
            [
                [x_start + hole_w, ymin, z0],
                [x_start, ymin, z0],
                [x_start, ymin, z1],
                [x_start + hole_w, ymin, z1],
            ],
            [
                [x_end, ymin, z0],
                [x_end - hole_w, ymin, z0],
                [x_end - hole_w, ymin, z1],
                [x_end, ymin, z1],
            ],
        ]
        # left/right (two each)
        y_start = ymin + d * side_margin
        y_end = ymax - d * side_margin
        hole_d = (y_end - y_start) * hole_frac
        pockets += [
            [
                [xmin, y_start, z0],
                [xmin, y_start + hole_d, z0],
                [xmin, y_start + hole_d, z1],
                [xmin, y_start, z1],
            ],
            [
                [xmin, y_end - hole_d, z0],
                [xmin, y_end, z0],
                [xmin, y_end, z1],
                [xmin, y_end - hole_d, z1],
            ],
            [
                [xmax, y_start + hole_d, z0],
                [xmax, y_start, z0],
                [xmax, y_start, z1],
                [xmax, y_start + hole_d, z1],
            ],
            [
                [xmax, y_end, z0],
                [xmax, y_end - hole_d, z0],
                [xmax, y_end - hole_d, z1],
                [xmax, y_end, z1],
            ],
        ]
        wm = obj.matrix_world
        return [[list(wm @ Vector(p)) for p in pocket] for pocket in pockets]

    def auto_expose_frame(self, sc, _cam_obj):
        """Enhanced auto-exposure with minimum brightness guarantee."""
        cfg = self.config
        if not cfg.get("enable_auto_exposure", True):
            return 0.0

        # Get current exposure settings
        target_ev = cfg.get("initial_exposure_ev", 0.0)

        # Ensure minimum brightness by checking if we have adequate lighting
        min_ev = cfg.get("exposure_min", -2.0)  # Minimum EV for adequate brightness
        max_ev = cfg.get("exposure_max", 4.0)  # Maximum EV to prevent overexposure

        # Check if we have sufficient lighting in the scene
        total_light_energy = 0.0
        light_count = 0

        for obj in bpy.data.objects:
            if obj.type == "LIGHT" and obj.data:
                total_light_energy += obj.data.energy
                light_count += 1

        # If lighting is too dim, boost exposure
        if light_count > 0:
            avg_light_energy = total_light_energy / light_count
            if avg_light_energy < 100:  # Low energy threshold
                target_ev = max(target_ev, min_ev + 1.0)  # Boost by at least 1 EV

        # Clamp exposure to reasonable range
        target_ev = max(min_ev, min(max_ev, target_ev))

        # Apply exposure
        sc.view_settings.exposure = target_ev

        return target_ev

    def detect_faces_in_scene(self, cam_obj, sc):
        """
        Detect faces in the scene by looking for pallet objects and extracting their faces.
        Uses the pallet's 3D bounding box to define 6 faces and generate keypoints for each visible face.
        """
        faces = []

        # Look for pallet objects (objects with "pallet" in name or pass_index > 0)
        min_area = self.config.get("keypoints_min_face_area", 100)
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH" and (
                obj.pass_index > 0 or "pallet" in obj.name.lower()
            ):
                # Skip objects that might be bottom/top faces or other non-pallet objects
                obj_name_lower = obj.name.lower()
                if any(
                    skip_word in obj_name_lower
                    for skip_word in ["down", "bottom", "top", "up", "face"]
                ):
                    continue

                # Get the pallet's 3D bounding box
                bbox_3d = self.bbox_3d_oriented(obj)
                corners_3d = [Vector(c) for c in bbox_3d["corners"]]

                # Get all 6 faces from 3D bounding box using proper Blender API approach
                all_faces = self.get_all_faces_from_bbox()

                # Identify top and bottom faces by Z coordinates
                side_faces = self.filter_side_faces(all_faces, corners_3d)

                # Collect all visible faces first
                visible_faces = []
                for _face_idx, face_data in enumerate(side_faces):
                    corner_indices = face_data["corners"]
                    face_name = face_data["name"]
                    # Preserve the original face index from the full face list
                    original_face_idx = all_faces.index(face_data)
                    # Get the 4 corners of this face
                    face_corners_3d = [corners_3d[i] for i in corner_indices]

                    # Calculate face center and dimensions
                    face_center = sum(face_corners_3d, Vector()) / 4

                    # Project face corners to 2D to check visibility
                    face_corners_2d = self.project_points(face_corners_3d, cam_obj, sc)
                    visible_corners = [p for p in face_corners_2d if p[2] > 0]

                    if (
                        len(visible_corners) >= 3
                    ):  # Face is visible if at least 3 corners are visible
                        # Calculate 2D bounding box for this face
                        xs, ys = zip(
                            *[(p[0], p[1]) for p in visible_corners], strict=False
                        )
                        x_min, x_max = min(xs), max(xs)
                        y_min, y_max = min(ys), max(ys)

                        face_area = (x_max - x_min) * (y_max - y_min)

                        if face_area > min_area:
                            # Calculate face normal to determine how directly it faces the camera
                            face_normal = self.calculate_face_normal(face_corners_3d)
                            camera_direction = (
                                cam_obj.location - face_center
                            ).normalized()
                            face_angle = abs(
                                face_normal.dot(camera_direction)
                            )  # Higher = more directly facing camera

                            visible_faces.append(
                                {
                                    "object": obj,
                                    "face_index": original_face_idx,
                                    "face_name": face_name,
                                    "face_center_3d": face_center,
                                    "face_corners_3d": face_corners_3d,
                                    "face_normal": face_normal,
                                    "face_angle": face_angle,
                                    "bbox_2d": {
                                        "x_min": x_min,
                                        "y_min": y_min,
                                        "x_max": x_max,
                                        "y_max": y_max,
                                        "width": x_max - x_min,
                                        "height": y_max - y_min,
                                        "area": face_area,
                                    },
                                    "bbox_3d": bbox_3d,
                                }
                            )

                # Select faces based on camera proximity and orientation
                selected_faces = self.select_faces_by_camera_proximity(
                    visible_faces, cam_obj
                )

                if selected_faces:
                    face_names = [f["face_name"] for f in selected_faces]
                    logger.info(
                        f"Selected {len(selected_faces)} faces by camera proximity: {face_names}"
                    )

                faces.extend(selected_faces)

        return faces

    def get_all_faces_from_bbox(self):
        """
        Get all 6 faces from 3D bounding box corners.
        Returns list of face data with corner indices and names.
        """
        # Standard 3D bounding box face definitions
        all_faces = [
            {"corners": [0, 1, 2, 3], "name": "face_0"},  # Face 0
            {"corners": [4, 5, 6, 7], "name": "face_1"},  # Face 1
            {"corners": [0, 1, 5, 4], "name": "face_2"},  # Face 2
            {"corners": [2, 3, 7, 6], "name": "face_3"},  # Face 3
            {"corners": [0, 3, 7, 4], "name": "face_4"},  # Face 4
            {"corners": [1, 2, 6, 5], "name": "face_5"},  # Face 5
        ]
        return all_faces

    def filter_side_faces(self, all_faces, corners_3d):
        """
        Filter out top and bottom faces by analyzing Z coordinates.
        Returns only the 4 side faces.
        """
        # Calculate Z coordinates for each face center
        face_z_coords = []
        for face in all_faces:
            face_corners = [corners_3d[i] for i in face["corners"]]
            face_center_z = sum(corner.z for corner in face_corners) / 4
            face_z_coords.append(face_center_z)

        # Sort faces by Z coordinate
        sorted_faces = sorted(
            zip(all_faces, face_z_coords, strict=False), key=lambda x: x[1]
        )

        # The top face has highest Z, bottom face has lowest Z
        # The 4 middle faces are the side faces
        side_faces = [
            face for face, _ in sorted_faces[1:-1]
        ]  # Exclude first (bottom) and last (top)

        return side_faces

    def create_3d_debug_visualization(self, obj, cam_obj, frame_id):
        """
        Create a 3D visualization showing camera position, pallet corners, and face names.
        Saves the visualization to a new debug folder.
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            logger.error("Matplotlib not available for 3D visualization")
            return

        # Use the debug_3d folder from setup_folders
        debug_folder = self.paths["debug_3d"]

        # Get pallet bounding box and corners
        bbox_3d = self.bbox_3d_oriented(obj)
        corners_3d = [Vector(c) for c in bbox_3d["corners"]]

        # Get camera position
        camera_pos = cam_obj.location

        # Create figure
        fig = plt.figure(figsize=(15, 10))
        ax = fig.add_subplot(111, projection="3d")

        # Plot pallet corners
        corner_x = [corner.x for corner in corners_3d]
        corner_y = [corner.y for corner in corners_3d]
        corner_z = [corner.z for corner in corners_3d]

        # Plot corners as large red dots
        ax.scatter(corner_x, corner_y, corner_z, c="red", s=100, label="Pallet Corners")

        # Label each corner
        for _i, corner in enumerate(corners_3d):
            ax.text(corner.x, corner.y, corner.z, f"  {_i}", fontsize=10, color="red")

        # Plot camera position
        ax.scatter(
            [camera_pos.x],
            [camera_pos.y],
            [camera_pos.z],
            c="blue",
            s=200,
            label="Camera",
            marker="^",
        )
        ax.text(
            camera_pos.x,
            camera_pos.y,
            camera_pos.z,
            "  Camera",
            fontsize=12,
            color="blue",
        )

        # Draw lines connecting corners to show the pallet structure
        # Define the edges of the bounding box
        edges = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],  # Bottom face
            [4, 5],
            [5, 6],
            [6, 7],
            [7, 4],  # Top face
            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7],  # Vertical edges
        ]

        for edge in edges:
            start = corners_3d[edge[0]]
            end = corners_3d[edge[1]]
            ax.plot(
                [start.x, end.x], [start.y, end.y], [start.z, end.z], "k-", alpha=0.3
            )

        # Get all faces and their centers
        all_faces = self.get_all_faces_from_bbox()
        side_faces = self.filter_side_faces(all_faces, corners_3d)

        # Plot face centers and labels
        face_colors = ["green", "orange", "purple", "brown", "pink", "gray"]
        for i, face in enumerate(all_faces):
            face_corners = [corners_3d[j] for j in face["corners"]]
            face_center = sum(face_corners, Vector()) / 4

            # Color side faces differently
            if face in side_faces:
                color = face_colors[i % len(face_colors)]
                size = 80
            else:
                color = "lightgray"
                size = 50

            ax.scatter(
                [face_center.x],
                [face_center.y],
                [face_center.z],
                c=color,
                s=size,
                alpha=0.7,
            )
            ax.text(
                face_center.x,
                face_center.y,
                face_center.z,
                f'  {face["name"]}',
                fontsize=9,
                color=color,
            )

        # Draw lines from camera to each corner for distance visualization
        for _i, corner in enumerate(corners_3d):
            distance = (camera_pos - corner).length
            ax.plot(
                [camera_pos.x, corner.x],
                [camera_pos.y, corner.y],
                [camera_pos.z, corner.z],
                "r--",
                alpha=0.3,
                linewidth=0.5,
            )
            # Add distance labels
            mid_x = (camera_pos.x + corner.x) / 2
            mid_y = (camera_pos.y + corner.y) / 2
            mid_z = (camera_pos.z + corner.z) / 2
            ax.text(mid_x, mid_y, mid_z, f"{distance:.1f}", fontsize=8, color="red")

        # Set labels and title
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(f"3D Debug View - Frame {frame_id}\nObject: {obj.name}")

        # Add legend
        ax.legend()

        # Set equal aspect ratio
        max_range = np.array(
            [
                corner_x + [camera_pos.x],
                corner_y + [camera_pos.y],
                corner_z + [camera_pos.z],
            ]
        ).flatten()
        max_range = max(max_range) - min(max_range)
        mid_x = (max(corner_x + [camera_pos.x]) + min(corner_x + [camera_pos.x])) * 0.5
        mid_y = (max(corner_y + [camera_pos.y]) + min(corner_y + [camera_pos.y])) * 0.5
        mid_z = (max(corner_z + [camera_pos.z]) + min(corner_z + [camera_pos.z])) * 0.5

        ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
        ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
        ax.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)

        # Save the plot
        output_path = os.path.join(debug_folder, f"frame_{frame_id:06d}_3d_debug.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"3D debug visualization saved to: {output_path}")

        # Also save coordinate data as text file
        coord_file = os.path.join(debug_folder, f"frame_{frame_id:06d}_coordinates.txt")
        with open(coord_file, "w") as f:
            f.write(f"Frame {frame_id} - 3D Coordinates Debug\n")
            f.write(f"Object: {obj.name}\n")
            f.write(
                f"Camera Position: ({camera_pos.x:.3f}, {camera_pos.y:.3f}, {camera_pos.z:.3f})\n\n"
            )

            f.write("Pallet Corners:\n")
            for _i, corner in enumerate(corners_3d):
                distance = (camera_pos - corner).length
                f.write(
                    f"  Corner {i}: ({corner.x:.3f}, {corner.y:.3f}, {corner.z:.3f}) - Distance: {distance:.3f}\n"
                )

            f.write("\nFace Centers:\n")
            for face in all_faces:
                face_corners = [corners_3d[j] for j in face["corners"]]
                face_center = sum(face_corners, Vector()) / 4
                distance = (camera_pos - face_center).length
                f.write(
                    f"  {face['name']}: ({face_center.x:.3f}, {face_center.y:.3f}, {face_center.z:.3f}) - Distance: {distance:.3f}\n"
                )

        logger.info(f"Coordinate data saved to: {coord_file}")

    def create_3d_debug_visualization_with_faces(
        self, obj, cam_obj, frame_id, selected_faces
    ):
        """
        Create a 3D visualization showing camera position, pallet corners, face names, and selected faces.
        Saves the visualization to the debug_3d folder.
        """
        logger.debug(f"Starting 3D visualization for {obj.name} (frame {frame_id})")

        try:
            import matplotlib.pyplot as plt
            import numpy as np

            logger.debug("Matplotlib imports successful")
        except ImportError as e:
            logger.error(f"Matplotlib not available for 3D visualization: {e}")
            return

        # Get pallet bounding box and corners
        bbox_3d = self.bbox_3d_oriented(obj)
        corners_3d = [Vector(c) for c in bbox_3d["corners"]]

        # Get camera position
        camera_pos = cam_obj.location

        # Create figure
        fig = plt.figure(figsize=(15, 10))
        ax = fig.add_subplot(111, projection="3d")

        # Plot pallet corners
        corner_x = [corner.x for corner in corners_3d]
        corner_y = [corner.y for corner in corners_3d]
        corner_z = [corner.z for corner in corners_3d]

        # Plot corners as large red dots
        ax.scatter(corner_x, corner_y, corner_z, c="red", s=100, label="Pallet Corners")

        # Label each corner
        for _i, corner in enumerate(corners_3d):
            ax.text(corner.x, corner.y, corner.z, f"  {_i}", fontsize=10, color="red")

        # Plot camera position
        ax.scatter(
            [camera_pos.x],
            [camera_pos.y],
            [camera_pos.z],
            c="blue",
            s=200,
            label="Camera",
            marker="^",
        )
        ax.text(
            camera_pos.x,
            camera_pos.y,
            camera_pos.z,
            "  Camera",
            fontsize=12,
            color="blue",
        )

        # Draw lines connecting corners to show the pallet structure
        edges = [
            [0, 1],
            [1, 2],
            [2, 3],
            [3, 0],  # Bottom face
            [4, 5],
            [5, 6],
            [6, 7],
            [7, 4],  # Top face
            [0, 4],
            [1, 5],
            [2, 6],
            [3, 7],  # Vertical edges
        ]

        for edge in edges:
            start = corners_3d[edge[0]]
            end = corners_3d[edge[1]]
            ax.plot(
                [start.x, end.x], [start.y, end.y], [start.z, end.z], "k-", alpha=0.3
            )

        # Get all faces and their centers
        all_faces = self.get_all_faces_from_bbox()
        side_faces = self.filter_side_faces(all_faces, corners_3d)

        # Get selected face names for this object
        selected_face_names = []
        for face_data in selected_faces:
            if face_data["object"] == obj:
                selected_face_names.append(face_data["face_name"])

        # Plot face centers and labels
        face_colors = ["green", "orange", "purple", "brown", "pink", "gray"]
        for i, face in enumerate(all_faces):
            face_corners = [corners_3d[j] for j in face["corners"]]
            face_center = sum(face_corners, Vector()) / 4

            # Determine color and size based on selection status
            if face["name"] in selected_face_names:
                # Selected face - bright color, larger size
                color = face_colors[i % len(face_colors)]
                size = 120
                marker = "o"
                label_suffix = " (SELECTED)"
            elif face in side_faces:
                # Side face but not selected - medium color, medium size
                color = "lightblue"
                size = 80
                marker = "s"
                label_suffix = " (side)"
            else:
                # Top/bottom face - light gray, small size
                color = "lightgray"
                size = 50
                marker = "^"
                label_suffix = " (top/bottom)"

            ax.scatter(
                [face_center.x],
                [face_center.y],
                [face_center.z],
                c=color,
                s=size,
                alpha=0.8,
                marker=marker,
            )
            ax.text(
                face_center.x,
                face_center.y,
                face_center.z,
                f'  {face["name"]}{label_suffix}',
                fontsize=9,
                color=color,
                weight="bold" if face["name"] in selected_face_names else "normal",
            )

        # Draw lines from camera to each corner for distance visualization
        for _i, corner in enumerate(corners_3d):
            distance = (camera_pos - corner).length
            ax.plot(
                [camera_pos.x, corner.x],
                [camera_pos.y, corner.y],
                [camera_pos.z, corner.z],
                "r--",
                alpha=0.3,
                linewidth=0.5,
            )
            # Add distance labels
            mid_x = (camera_pos.x + corner.x) / 2
            mid_y = (camera_pos.y + corner.y) / 2
            mid_z = (camera_pos.z + corner.z) / 2
            ax.text(mid_x, mid_y, mid_z, f"{distance:.1f}", fontsize=8, color="red")

        # Set labels and title
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")
        ax.set_title(
            f"3D Debug View - Frame {frame_id}\nObject: {obj.name}\nSelected Faces: {', '.join(selected_face_names) if selected_face_names else 'None'}"
        )

        # Add legend
        ax.legend()

        # Set equal aspect ratio
        max_range = np.array(
            [
                corner_x + [camera_pos.x],
                corner_y + [camera_pos.y],
                corner_z + [camera_pos.z],
            ]
        ).flatten()
        max_range = max(max_range) - min(max_range)
        mid_x = (max(corner_x + [camera_pos.x]) + min(corner_x + [camera_pos.x])) * 0.5
        mid_y = (max(corner_y + [camera_pos.y]) + min(corner_y + [camera_pos.y])) * 0.5
        mid_z = (max(corner_z + [camera_pos.z]) + min(corner_z + [camera_pos.z])) * 0.5

        ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
        ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
        ax.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)

        # Save the plot as PNG image
        output_path = os.path.join(
            self.paths["debug_3d_images"], f"frame_{frame_id:06d}_3d_debug.png"
        )

        try:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            logger.info(f"3D debug visualization saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving 3D plot: {e}")
            plt.close()
            return

        # Save interactive 3D figure using plotly (if available)
        interactive_path = os.path.join(
            self.paths["debug_3d_figures"], f"frame_{frame_id:06d}_3d_interactive.html"
        )
        try:
            self.create_interactive_3d_figure(
                corners_3d, camera_pos, selected_faces, frame_id, interactive_path
            )
            logger.info(f"Interactive 3D figure saved to: {interactive_path}")
        except Exception as e:
            logger.warning(f"Could not save interactive figure: {e}")

        plt.close()

        # Also save coordinate data as text file
        coord_file = os.path.join(
            self.paths["debug_3d_coordinates"], f"frame_{frame_id:06d}_coordinates.txt"
        )

        try:
            with open(coord_file, "w") as f:
                f.write(f"Frame {frame_id} - 3D Coordinates Debug\n")
                f.write(f"Object: {obj.name}\n")
                f.write(
                    f"Camera Position: ({camera_pos.x:.3f}, {camera_pos.y:.3f}, {camera_pos.z:.3f})\n"
                )
                f.write(
                    f"Selected Faces: {', '.join(selected_face_names) if selected_face_names else 'None'}\n\n"
                )

                f.write("Pallet Corner Points (8 corners):\n")
                for _i, corner in enumerate(corners_3d):
                    distance = (camera_pos - corner).length
                    f.write(
                        f"  Corner {i}: ({corner.x:.3f}, {corner.y:.3f}, {corner.z:.3f}) - Distance: {distance:.3f}\n"
                    )

                f.write("\nAll Face Definitions (6 faces total):\n")
                for face in all_faces:
                    face_corners = [corners_3d[j] for j in face["corners"]]
                    face_center = sum(face_corners, Vector()) / 4
                    distance = (camera_pos - face_center).length
                    status = (
                        "SELECTED"
                        if face["name"] in selected_face_names
                        else "not selected"
                    )
                    f.write(f"  {face['name']} (corners {face['corners']}):\n")
                    f.write(
                        f"    Center: ({face_center.x:.3f}, {face_center.y:.3f}, {face_center.z:.3f}) - Distance: {distance:.3f}\n"
                    )
                    f.write(f"    Status: {status}\n")
                    f.write("    Corner Points:\n")
                    for corner_idx in face["corners"]:
                        corner = corners_3d[corner_idx]
                        corner_dist = (camera_pos - corner).length
                        f.write(
                            f"      Corner {corner_idx}: ({corner.x:.3f}, {corner.y:.3f}, {corner.z:.3f}) - Distance: {corner_dist:.3f}\n"
                        )
                    f.write("\n")

                f.write("Selected Face Details:\n")
                if selected_face_names:
                    for face_data in selected_faces:
                        if face_data["object"] == obj:
                            face_name = face_data["face_name"]
                            face_index = face_data["face_index"]
                            f.write(f"  {face_name} (index {face_index}):\n")

                            # Get the face definition
                            face_def = None
                            for face in all_faces:
                                if face["name"] == face_name:
                                    face_def = face
                                    break

                            if face_def:
                                face_corners = [
                                    corners_3d[j] for j in face_def["corners"]
                                ]
                                face_center = sum(face_corners, Vector()) / 4
                                distance = (camera_pos - face_center).length
                                f.write(
                                    f"    Center Position: ({face_center.x:.3f}, {face_center.y:.3f}, {face_center.z:.3f})\n"
                                )
                                f.write(f"    Distance from Camera: {distance:.3f}\n")
                                f.write(f"    Corner Indices: {face_def['corners']}\n")
                                f.write("    Corner Positions:\n")
                                for corner_idx in face_def["corners"]:
                                    corner = corners_3d[corner_idx]
                                    corner_dist = (camera_pos - corner).length
                                    f.write(
                                        f"      Corner {corner_idx}: ({corner.x:.3f}, {corner.y:.3f}, {corner.z:.3f}) - Distance: {corner_dist:.3f}\n"
                                    )

                                # Add 2D bounding box info if available
                                if "bbox_2d" in face_data:
                                    bbox_2d = face_data["bbox_2d"]
                                    f.write(
                                        f"    2D Bounding Box: x_min={bbox_2d['x_min']:.1f}, y_min={bbox_2d['y_min']:.1f}, x_max={bbox_2d['x_max']:.1f}, y_max={bbox_2d['y_max']:.1f}\n"
                                    )

                                # Add 3D bounding box info if available
                                if "bbox_3d" in face_data:
                                    bbox_3d = face_data["bbox_3d"]
                                    f.write(f"    3D Bounding Box: {bbox_3d}\n")

                                f.write("\n")
                else:
                    f.write("  No faces selected for this object.\n")

            logger.info(f"Coordinate data saved to: {coord_file}")
        except Exception as e:
            logger.error(f"Error saving coordinate data: {e}")
            return

    def select_faces_by_camera_proximity(self, visible_faces, cam_obj):
        """
        Select faces based on camera proximity using nearest point distance.
        Returns 1-2 faces: first the nearest face, then an adjacent candidate if available.
        """
        if not visible_faces:
            return []

        # Step 1: Calculate face scores for each face
        face_scores = []
        for face in visible_faces:
            face_corners = face["face_corners_3d"]

            # Calculate distance from camera to each corner
            corner_distances = []
            for corner in face_corners:
                distance = (cam_obj.location - corner).length
                corner_distances.append(distance)

            # Calculate multiple metrics for better face selection
            nearest_distance = min(corner_distances)
            avg_distance = sum(corner_distances) / len(corner_distances)

            # Count corners within reasonable distance (within 1.5x of nearest)
            close_corners = sum(
                1 for d in corner_distances if d <= nearest_distance * 1.5
            )

            # Calculate face score: prioritize faces with more close corners and better average distance
            # Lower score is better (closer to camera)
            face_score = (
                nearest_distance
                + (avg_distance - nearest_distance) * 0.3
                - close_corners * 0.1
            )

            face_scores.append(
                (face, face_score, nearest_distance, avg_distance, corner_distances)
            )

        # Step 2: Check if we have any valid faces
        if not face_scores:
            logger.warning("No valid faces found for selection")
            return []

        # Sort by face score (lower is better)
        face_scores.sort(key=lambda x: x[1])

        # Step 3: Select the face with the best score
        selected_faces = []
        primary_face = face_scores[0][0]
        selected_faces.append(primary_face)

        logger.info(
            f"Selected primary face: {primary_face['face_name']} (score: {face_scores[0][1]:.2f}, nearest: {face_scores[0][2]:.2f})"
        )

        # Step 4: Look for adjacent candidates (left/right)
        if len(face_scores) > 1:
            adjacent_candidates = []

            for (
                face,
                face_score,
                nearest_distance,
                avg_distance,
                corner_distances,
            ) in face_scores[1:]:
                # Check if this face is adjacent to the primary face
                is_adjacent = self.check_faces_adjacent(primary_face, face)

                if is_adjacent:
                    # Use the face score for adjacent candidate selection
                    adjacent_candidates.append(
                        (
                            face,
                            face_score,
                            nearest_distance,
                            avg_distance,
                            corner_distances,
                        )
                    )

            # Step 5: Select the best adjacent candidate based on face score
            if adjacent_candidates:
                # Sort by face score (lower is better)
                adjacent_candidates.sort(key=lambda x: x[1])
                best_adjacent = adjacent_candidates[0][0]

                # Check if the adjacent candidate has sufficient 2D surface area and is not behind primary
                surface_quality_good = self.check_2d_surface_quality(
                    best_adjacent,
                    self.config.get("resolution", [1024, 768])[0],
                    self.config.get("resolution", [1024, 768])[1],
                )

                not_behind_primary = not self.check_face_behind_primary(
                    primary_face, best_adjacent
                )

                if surface_quality_good and not_behind_primary:
                    selected_faces.append(best_adjacent)
                    logger.info(
                        f"Selected adjacent face: {best_adjacent['face_name']} (score: {adjacent_candidates[0][1]:.2f}, nearest: {adjacent_candidates[0][2]:.2f})"
                    )
                else:
                    if not surface_quality_good:
                        logger.info(
                            f"Adjacent candidate {best_adjacent['face_name']} rejected due to poor 2D surface quality"
                        )
                    if not not_behind_primary:
                        logger.info(
                            f"Adjacent candidate {best_adjacent['face_name']} rejected because it's behind the primary face"
                        )
            else:
                # Fallback: Try to find adjacent faces without 2D middle view check
                fallback_candidates = []

                for (
                    face,
                    face_score,
                    nearest_distance,
                    avg_distance,
                    corner_distances,
                ) in face_scores[1:]:
                    # Check only geometric adjacency (skip 2D middle view check)
                    if self.check_geometric_adjacency_only(primary_face, face):
                        fallback_candidates.append(
                            (
                                face,
                                face_score,
                                nearest_distance,
                                avg_distance,
                                corner_distances,
                            )
                        )

                if fallback_candidates:
                    # Sort by face score (lower is better)
                    fallback_candidates.sort(key=lambda x: x[1])
                    best_fallback = fallback_candidates[0][0]

                    # Check if the fallback candidate has sufficient 2D surface area and is not behind primary
                    surface_quality_good = self.check_2d_surface_quality(
                        best_fallback,
                        self.config.get("resolution", [1024, 768])[0],
                        self.config.get("resolution", [1024, 768])[1],
                    )

                    not_behind_primary = not self.check_face_behind_primary(
                        primary_face, best_fallback
                    )

                    if surface_quality_good and not_behind_primary:
                        selected_faces.append(best_fallback)
                        logger.info(
                            f"Selected fallback adjacent face: {best_fallback['face_name']} (score: {fallback_candidates[0][1]:.2f})"
                        )
                    else:
                        if not surface_quality_good:
                            logger.info(
                                f"Fallback candidate {best_fallback['face_name']} rejected due to poor 2D surface quality"
                            )
                        if not not_behind_primary:
                            logger.info(
                                f"Fallback candidate {best_fallback['face_name']} rejected because it's behind the primary face"
                            )
                else:
                    logger.info(
                        "No valid adjacent candidates found, using only primary face"
                    )

        return selected_faces

    def check_faces_adjacent(self, face1, face2, tolerance=0.1):
        """
        Check if two faces are truly adjacent (side-by-side), NEVER parallel.
        Uses strict geometric analysis to ensure only side-by-side faces are selected.
        """
        # STRICT RULE: Only allow adjacent faces, never parallel ones

        # Method 1: Check face indices - only allow specific adjacent pairs
        face1_idx = face1.get("face_index", -1)
        face2_idx = face2.get("face_index", -1)

        # Define ONLY the allowed adjacent pairs (side-by-side, never parallel)
        # These are the only combinations that represent truly adjacent faces
        allowed_adjacent_pairs = [
            (0, 2),  # Front-Left
            (0, 3),  # Front-Right
            (1, 2),  # Back-Left
            (1, 3),  # Back-Right
        ]

        # Check if this is an allowed adjacent pair
        is_allowed_pair = (face1_idx, face2_idx) in allowed_adjacent_pairs or (
            face2_idx,
            face1_idx,
        ) in allowed_adjacent_pairs

        if not is_allowed_pair:
            return False

        # Method 2: Verify they share exactly 2 corners (geometric validation)
        face1_corners = face1["face_corners_3d"]
        face2_corners = face2["face_corners_3d"]

        shared_corners = 0
        for corner1 in face1_corners:
            for corner2 in face2_corners:
                distance = (corner1 - corner2).length
                if distance < tolerance:
                    shared_corners += 1
                    break

        # Adjacent faces should share exactly 2 corners (the edge between them)
        if shared_corners != 2:
            return False

        # Method 3: Check 2D box middle view (50% of box size)
        return self.check_2d_middle_view(face1, face2)

    def check_2d_middle_view(self, face1, face2):
        """
        Check if both faces are in the middle view of the 2D bounding box.
        Middle view = within 50% of the box size from center.
        """
        bbox1 = face1["bbox_2d"]
        bbox2 = face2["bbox_2d"]

        # Calculate center of each face's 2D bounding box
        center1_x = (bbox1["x_min"] + bbox1["x_max"]) / 2
        center1_y = (bbox1["y_min"] + bbox1["y_max"]) / 2
        center2_x = (bbox2["x_min"] + bbox2["x_max"]) / 2
        center2_y = (bbox2["y_min"] + bbox2["y_max"]) / 2

        # Calculate the combined bounding box
        combined_x_min = min(bbox1["x_min"], bbox2["x_min"])
        combined_x_max = max(bbox1["x_max"], bbox2["x_max"])
        combined_y_min = min(bbox1["y_min"], bbox2["y_min"])
        combined_y_max = max(bbox1["y_max"], bbox2["y_max"])

        # Calculate center of combined box
        combined_center_x = (combined_x_min + combined_x_max) / 2
        combined_center_y = (combined_y_min + combined_y_max) / 2

        # Calculate 50% margins from center (increased from 30% to be less restrictive)
        box_width = combined_x_max - combined_x_min
        box_height = combined_y_max - combined_y_min
        margin_x = box_width * 0.5
        margin_y = box_height * 0.5

        # Check if both face centers are within 50% of the combined box center
        face1_in_middle = (
            abs(center1_x - combined_center_x) <= margin_x
            and abs(center1_y - combined_center_y) <= margin_y
        )
        face2_in_middle = (
            abs(center2_x - combined_center_x) <= margin_x
            and abs(center2_y - combined_center_y) <= margin_y
        )

        return face1_in_middle and face2_in_middle

    def check_geometric_adjacency_only(self, face1, face2, tolerance=0.1):
        """
        Check if two faces are geometrically adjacent (only geometric validation, no 2D check).
        This is used as a fallback when the full adjacency check fails.
        """
        # Method 1: Check face indices - only allow specific adjacent pairs
        face1_idx = face1.get("face_index", -1)
        face2_idx = face2.get("face_index", -1)

        # Define ONLY the allowed adjacent pairs (side-by-side, never parallel)
        allowed_adjacent_pairs = [
            (0, 2),  # Front-Left
            (0, 3),  # Front-Right
            (1, 2),  # Back-Left
            (1, 3),  # Back-Right
        ]

        # Check if this is an allowed adjacent pair
        is_allowed_pair = (face1_idx, face2_idx) in allowed_adjacent_pairs or (
            face2_idx,
            face1_idx,
        ) in allowed_adjacent_pairs

        if not is_allowed_pair:
            return False

        # Method 2: Verify they share exactly 2 corners (geometric validation)
        face1_corners = face1["face_corners_3d"]
        face2_corners = face2["face_corners_3d"]

        shared_corners = 0
        for corner1 in face1_corners:
            for corner2 in face2_corners:
                distance = (corner1 - corner2).length
                if distance < tolerance:
                    shared_corners += 1
                    break

        # Adjacent faces should share exactly 2 corners (the edge between them)
        return shared_corners == 2

    def check_2d_surface_quality(
        self,
        face,
        image_width=1024,
        image_height=768,
        min_area=2000,  # Reduced from 5000 to 2000 for more permissive selection
        min_width=30,  # Reduced from 50 to 30
        min_height=30,  # Reduced from 50 to 30
    ):
        """
        Check if a face has sufficient 2D surface quality to be selected as a candidate.

        Args:
            face: Face data containing bbox_2d
            image_width: Width of the rendered image
            image_height: Height of the rendered image
            min_area: Minimum 2D bounding box area in pixels
            min_width: Minimum width in pixels
            min_height: Minimum height in pixels

        Returns:
            True if the face has good 2D surface quality, False otherwise
        """
        bbox = face["bbox_2d"]

        # Calculate 2D bounding box dimensions
        width = bbox["x_max"] - bbox["x_min"]
        height = bbox["y_max"] - bbox["y_min"]
        area = width * height

        # Check minimum requirements
        has_sufficient_area = area >= min_area
        has_sufficient_width = width >= min_width
        has_sufficient_height = height >= min_height

        # Additional check: ensure the face is not too skewed (aspect ratio check)
        aspect_ratio = (
            max(width, height) / min(width, height)
            if min(width, height) > 0
            else float("inf")
        )
        has_reasonable_aspect_ratio = aspect_ratio <= 10.0  # Not too elongated

        # Check if face is not too close to image edges (indicating partial visibility)
        margin = min(
            50, min(image_width, image_height) * 0.05
        )  # 5% of smaller dimension or 50px max

        not_too_close_to_edges = (
            bbox["x_min"] >= margin
            and bbox["x_max"] <= image_width - margin
            and bbox["y_min"] >= margin
            and bbox["y_max"] <= image_height - margin
        )

        quality_good = (
            has_sufficient_area
            and has_sufficient_width
            and has_sufficient_height
            and has_reasonable_aspect_ratio
            and not_too_close_to_edges
        )

        return quality_good

    def check_face_behind_primary(self, primary_face, candidate_face):
        """
        Check if the candidate face has points between the primary face's points,
        which indicates the candidate is behind the camera view.

        Args:
            primary_face: The primary selected face
            candidate_face: The candidate face to check

        Returns:
            True if candidate is behind primary (should be eliminated), False otherwise
        """
        primary_bbox = primary_face["bbox_2d"]
        candidate_bbox = candidate_face["bbox_2d"]

        # Get the primary face's bounding box coordinates
        primary_x_min, primary_x_max = primary_bbox["x_min"], primary_bbox["x_max"]
        primary_y_min, primary_y_max = primary_bbox["y_min"], primary_bbox["y_max"]

        # Get the candidate face's bounding box coordinates
        candidate_x_min, candidate_x_max = (
            candidate_bbox["x_min"],
            candidate_bbox["x_max"],
        )
        candidate_y_min, candidate_y_max = (
            candidate_bbox["y_min"],
            candidate_bbox["y_max"],
        )

        # Check if candidate's center is between primary's bounds
        candidate_center_x = (candidate_x_min + candidate_x_max) / 2
        candidate_center_y = (candidate_y_min + candidate_y_max) / 2

        # Check if candidate center is within primary face bounds
        center_between_primary = (
            primary_x_min <= candidate_center_x <= primary_x_max
            and primary_y_min <= candidate_center_y <= primary_y_max
        )

        # Check if candidate overlaps significantly with primary (indicating it's behind)
        overlap_x = max(
            0, min(candidate_x_max, primary_x_max) - max(candidate_x_min, primary_x_min)
        )
        overlap_y = max(
            0, min(candidate_y_max, primary_y_max) - max(candidate_y_min, primary_y_min)
        )
        overlap_area = overlap_x * overlap_y

        # Calculate candidate area
        candidate_area = (candidate_x_max - candidate_x_min) * (
            candidate_y_max - candidate_y_min
        )

        # If overlap is more than 50% of candidate area, it's likely behind (increased from 30% to 50% for more permissive selection)
        overlap_ratio = overlap_area / candidate_area if candidate_area > 0 else 0
        significant_overlap = overlap_ratio > 0.5

        # Check if candidate is completely contained within primary bounds
        completely_contained = (
            primary_x_min <= candidate_x_min
            and candidate_x_max <= primary_x_max
            and primary_y_min <= candidate_y_min
            and candidate_y_max <= primary_y_max
        )

        is_behind = (
            center_between_primary or significant_overlap or completely_contained
        )

        return is_behind

    def detect_overlapping_keypoints(self, all_keypoints, keypoints_data, threshold=10):
        """
        Detect keypoints that are overlapping (within threshold pixels).
        Returns groups of overlapping keypoints with face data.
        """
        overlap_groups = []
        processed = set()

        for i, kp1 in enumerate(all_keypoints):
            if i in processed:
                continue

            x1, y1 = int(kp1["kp"]["position_2d"][0]), int(kp1["kp"]["position_2d"][1])
            if x1 <= 0 or y1 <= 0:
                continue

            group = [kp1]
            processed.add(i)

            for j, kp2 in enumerate(all_keypoints[i + 1 :], i + 1):
                if j in processed:
                    continue

                x2, y2 = int(kp2["kp"]["position_2d"][0]), int(
                    kp2["kp"]["position_2d"][1]
                )
                if x2 <= 0 or y2 <= 0:
                    continue

                distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                if distance <= threshold:
                    group.append(kp2)
                    processed.add(j)

            if len(group) > 1:
                # Add face_data to each keypoint in the group
                enhanced_group = []
                for kp_item in group:
                    face_idx = kp_item["face_idx"]
                    face_data = (
                        keypoints_data[face_idx]
                        if face_idx < len(keypoints_data)
                        else {}
                    )
                    enhanced_item = kp_item.copy()
                    enhanced_item["face_data"] = face_data
                    enhanced_group.append(enhanced_item)
                overlap_groups.append(enhanced_group)

        return overlap_groups

    def draw_overlapping_keypoint_circles(self, draw, overlap_group, x, y):
        """
        Draw overlapping keypoints with both colors (one inside the other).
        The face with smaller perimeter gets the inner color.
        """
        # Sort overlap group by face index for consistent ordering
        overlap_group.sort(key=lambda item: item["face_idx"])

        # Calculate perimeters for each face in the overlap group
        face_perimeters = {}
        for group_item in overlap_group:
            face_idx = group_item["face_idx"]
            if face_idx not in face_perimeters:
                # Calculate face perimeter from bbox_2d
                face_data = group_item.get("face_data", {})
                bbox = face_data.get("bbox_2d", {})
                if bbox:
                    width = bbox.get("x_max", 0) - bbox.get("x_min", 0)
                    height = bbox.get("y_max", 0) - bbox.get("y_min", 0)
                    face_perimeters[face_idx] = 2 * (width + height)
                else:
                    face_perimeters[face_idx] = 0

        # Sort by perimeter (smaller perimeter = inner circle)
        sorted_faces = sorted(
            overlap_group, key=lambda item: face_perimeters.get(item["face_idx"], 0)
        )

        # Draw outer circle (larger perimeter)
        if len(sorted_faces) >= 2:
            outer_face = sorted_faces[-1]  # Largest perimeter
            outer_color = outer_face["face_color"]
            outer_radius = 6
            draw.ellipse(
                [
                    x - outer_radius,
                    y - outer_radius,
                    x + outer_radius,
                    y + outer_radius,
                ],
                fill=outer_color,
                outline=(0, 0, 0),
                width=2,
            )

            # Draw inner circle (smaller perimeter)
            inner_face = sorted_faces[0]  # Smallest perimeter
            inner_color = inner_face["face_color"]
            inner_radius = 4
            draw.ellipse(
                [
                    x - inner_radius,
                    y - inner_radius,
                    x + inner_radius,
                    y + inner_radius,
                ],
                fill=inner_color,
                outline=(0, 0, 0),
                width=1,
            )
        else:
            # Fallback: just draw one circle
            face_color = overlap_group[0]["face_color"]
            radius = 6
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=face_color,
                outline=(0, 0, 0),
                width=2,
            )

    def draw_single_keypoint_labels(self, draw, font, kp, x, y, radius, color_text):
        """Draw labels for a single keypoint."""
        # Draw keypoint name
        label = kp["name"]
        w_txt, h_txt = self._text_wh(draw, label, font)
        draw.text(
            (x + radius + 2, y - h_txt // 2),
            label,
            fill=color_text,
            font=font,
        )

        # Draw 3D coordinates if enabled
        if self.config.get("keypoints_show_3d_labels", True):
            pos_3d = kp["position_3d"]
            coord_3d_text = f"3D: ({pos_3d[0]:.2f}, {pos_3d[1]:.2f}, {pos_3d[2]:.2f})"
            w_3d, h_3d = self._text_wh(draw, coord_3d_text, font)
            draw.text(
                (x + radius + 2, y + h_txt // 2 + 2),
                coord_3d_text,
                fill=(255, 200, 0),  # Orange color for 3D coordinates
                font=font,
            )

        # Draw 2D coordinates if enabled
        if self.config.get("keypoints_show_2d_labels", True):
            pos_2d = kp["position_2d"]
            coord_2d_text = f"2D: ({pos_2d[0]:.0f}, {pos_2d[1]:.0f})"
            w_2d, h_2d = self._text_wh(draw, coord_2d_text, font)
            y_offset = y + h_txt // 2 + 2
            if self.config.get("keypoints_show_3d_labels", True):
                y_offset += h_3d + 2  # Offset below 3D coordinates
            draw.text(
                (x + radius + 2, y_offset),
                coord_2d_text,
                fill=(0, 255, 200),  # Cyan color for 2D coordinates
                font=font,
            )

    def draw_overlapping_keypoint_labels(self, draw, font, overlap_group, x, y, radius):
        """Draw stacked labels for overlapping keypoints."""
        # Sort overlap group by face index for consistent ordering
        overlap_group.sort(key=lambda item: item["face_idx"])

        y_offset = y - radius - 5  # Start above the keypoint

        for _i, group_item in enumerate(overlap_group):
            group_kp = group_item["kp"]
            face_color = group_item["face_color"]
            face_name = group_item["face_name"]

            # Draw face name and keypoint name
            label = f"{face_name}: {group_kp['name']}"
            w_txt, h_txt = self._text_wh(draw, label, font)

            # Draw background rectangle for better visibility
            draw.rectangle(
                [
                    x + radius + 2,
                    y_offset - 2,
                    x + radius + 2 + w_txt + 4,
                    y_offset + h_txt + 2,
                ],
                fill=(255, 255, 255, 200),  # Semi-transparent white background
                outline=face_color,
                width=1,
            )

            draw.text(
                (x + radius + 4, y_offset),
                label,
                fill=face_color,
                font=font,
            )

            y_offset += h_txt + 2  # Move down for next label

    def calculate_face_normal(self, face_corners_3d):
        """Calculate the normal vector of a face from its 4 corners."""
        # Use first 3 corners to calculate normal
        v1 = face_corners_3d[1] - face_corners_3d[0]
        v2 = face_corners_3d[2] - face_corners_3d[0]
        normal = v1.cross(v2)
        return normal.normalized()

    def generate_keypoints_for_frame(self, cam_obj, sc, frame_id=None):
        """Generate keypoints for all faces detected in the current frame."""
        # Detect faces in the scene
        faces = self.detect_faces_in_scene(cam_obj, sc)

        # Create 3D debug visualization AFTER face calculations are complete
        if frame_id is not None:
            logger.info(f"Creating 3D debug visualization for frame {frame_id}")

            pallet_objects_found = 0
            for obj in bpy.context.scene.objects:
                if obj.type == "MESH" and (
                    obj.pass_index > 0 or "pallet" in obj.name.lower()
                ):
                    # Skip objects that might be bottom/top faces or other non-pallet objects
                    obj_name_lower = obj.name.lower()
                    if any(
                        skip_word in obj_name_lower
                        for skip_word in ["down", "bottom", "top", "up", "face"]
                    ):
                        continue

                    pallet_objects_found += 1
                    logger.info(
                        f"Creating 3D visualization for pallet object: {obj.name}"
                    )

                    # Create 3D visualization for this object with selected faces info
                    try:
                        self.create_3d_debug_visualization_with_faces(
                            obj, cam_obj, frame_id, faces
                        )
                        logger.info(f"3D visualization created for {obj.name}")
                    except Exception as e:
                        logger.error(
                            f"Error creating 3D visualization for {obj.name}: {e}"
                        )
                        import traceback

                        traceback.print_exc()

            if pallet_objects_found == 0:
                logger.warning(
                    f"No pallet objects found for 3D visualization in frame {frame_id}"
                )
            else:
                logger.info(
                    f"Processed {pallet_objects_found} pallet objects for 3D visualization"
                )

        # Only generate keypoints if enabled
        if not self.config.get("generate_keypoints", True):
            return []

        keypoints_data = []
        for face_data in faces:
            # Generate keypoints for this face
            keypoints = self.generate_face_keypoints(face_data, cam_obj, sc)

            # Add to keypoints data
            keypoints_data.append(
                {
                    "face_object": face_data["object"],
                    "face_name": face_data["face_name"],
                    "face_index": face_data["face_index"],
                    "bbox_2d": face_data["bbox_2d"],
                    "bbox_3d": face_data["bbox_3d"],
                    "face_corners_3d": face_data["face_corners_3d"],
                    "keypoints": keypoints,
                }
            )

        # Generate 2D boxes and 3D coordinates for selected faces
        if frame_id is not None:
            # Get image dimensions from config
            img_width = self.config.get("resolution", [1024, 768])[0]
            img_height = self.config.get("resolution", [1024, 768])[1]
            self.generate_face_2d_boxes(faces, frame_id, img_width, img_height)
            self.generate_face_3d_coordinates(faces, frame_id, img_width, img_height)

        return keypoints_data

    def generate_face_2d_boxes(self, selected_faces, frame_id, img_width, img_height):
        """Generate 2D bounding boxes for selected faces in YOLO format."""
        if not selected_faces:
            return

        # Create output file for 2D boxes in YOLO format
        output_file = os.path.join(
            self.paths["face_2d_boxes"], f"frame_{frame_id:06d}_2d_boxes.txt"
        )

        with open(output_file, "w") as f:
            f.write(
                f"# 2D Bounding Boxes for Selected Faces - Frame {frame_id} (YOLO Format)\n"
            )
            f.write(
                "# Format: class_id x_center y_center width height (normalized 0-1)\n"
            )
            f.write(f"# Total faces: {len(selected_faces)}\n\n")

            for face_idx, face_data in enumerate(selected_faces):
                bbox_2d = face_data["bbox_2d"]

                x_min = bbox_2d["x_min"]
                y_min = bbox_2d["y_min"]
                x_max = bbox_2d["x_max"]
                y_max = bbox_2d["y_max"]

                # Convert to YOLO format (normalized center coordinates and dimensions)
                x_center = (x_min + x_max) / 2.0 / img_width
                y_center = (y_min + y_max) / 2.0 / img_height
                width = (x_max - x_min) / img_width
                height = (y_max - y_min) / img_height

                # Use face index as class_id (0, 1, 2, etc.)
                class_id = face_idx

                f.write(
                    f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"
                )

    def generate_face_3d_coordinates(
        self, selected_faces, frame_id, img_width, img_height
    ):
        """Generate 3D coordinates for selected faces in YOLO format."""
        if not selected_faces:
            return

        # Create output file for 3D coordinates in YOLO format
        output_file = os.path.join(
            self.paths["face_3d_coordinates"],
            f"frame_{frame_id:06d}_3d_coordinates.txt",
        )

        with open(output_file, "w") as f:
            f.write(
                f"# 3D Coordinates for Selected Faces - Frame {frame_id} (YOLO Format)\n"
            )
            f.write(
                "# Format: class_id x_center y_center width height kp1_x kp1_y kp1_v kp2_x kp2_y kp2_v ...\n"
            )
            f.write(f"# Total faces: {len(selected_faces)}\n\n")

            for face_idx, face_data in enumerate(selected_faces):
                face_corners_3d = face_data["face_corners_3d"]
                bbox_2d = face_data["bbox_2d"]

                # Calculate 2D bounding box in YOLO format
                x_min = bbox_2d["x_min"]
                y_min = bbox_2d["y_min"]
                x_max = bbox_2d["x_max"]
                y_max = bbox_2d["y_max"]

                x_center = (x_min + x_max) / 2.0 / img_width
                y_center = (y_min + y_max) / 2.0 / img_height
                width = (x_max - x_min) / img_width
                height = (y_max - y_min) / img_height

                # Use face index as class_id
                class_id = face_idx

                # Start the line with YOLO bbox format
                line = (
                    f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                )

                # Add 3D corner points as keypoints (projected to 2D)
                for corner in face_corners_3d:
                    # Project 3D point to 2D (this would need camera context, using bbox for now)
                    # For now, we'll use the corner positions relative to the bbox
                    corner_x = (
                        (corner.x - x_min) / (x_max - x_min) if x_max > x_min else 0.5
                    )
                    corner_y = (
                        (corner.y - y_min) / (y_max - y_min) if y_max > y_min else 0.5
                    )
                    visibility = 2  # Always visible for 3D coordinates

                    line += f" {corner_x:.6f} {corner_y:.6f} {visibility}"

                f.write(f"{line}\n")

    def create_interactive_3d_figure(
        self, corners_3d, camera_pos, selected_faces, frame_id, output_path
    ):
        """
        Create an interactive 3D figure using plotly that can be opened and manipulated in a browser.
        """
        try:
            import plotly.graph_objects as go
            import plotly.offline as pyo
        except ImportError:
            logger.warning("Plotly not available for interactive 3D figures")
            return

        # Create figure
        fig = go.Figure()

        # Add pallet corners
        corner_x = [corner.x for corner in corners_3d]
        corner_y = [corner.y for corner in corners_3d]
        corner_z = [corner.z for corner in corners_3d]

        fig.add_trace(
            go.Scatter3d(
                x=corner_x,
                y=corner_y,
                z=corner_z,
                mode="markers+text",
                marker={"size": 8, "color": "red", "symbol": "circle"},
                text=[f"Corner {i}" for i in range(len(corners_3d))],
                textposition="top center",
                name="Pallet Corners",
            )
        )

        # Add camera position
        fig.add_trace(
            go.Scatter3d(
                x=[camera_pos.x],
                y=[camera_pos.y],
                z=[camera_pos.z],
                mode="markers+text",
                marker={"size": 12, "color": "blue", "symbol": "diamond"},
                text=["Camera"],
                textposition="top center",
                name="Camera",
            )
        )

        # Add lines from camera to corners
        for _i, corner in enumerate(corners_3d):
            fig.add_trace(
                go.Scatter3d(
                    x=[camera_pos.x, corner.x],
                    y=[camera_pos.y, corner.y],
                    z=[camera_pos.z, corner.z],
                    mode="lines",
                    line={"color": "gray", "width": 2, "dash": "dash"},
                    showlegend=False,
                    name=f"Camera to Corner {_i}",
                )
            )

        # Add selected faces
        if selected_faces:
            face_colors = ["green", "orange", "purple", "brown"]
            for i, face_data in enumerate(selected_faces):
                face_corners_3d = face_data.get("face_corners_3d", [])
                if face_corners_3d:
                    face_x = [corner.x for corner in face_corners_3d]
                    face_y = [corner.y for corner in face_corners_3d]
                    face_z = [corner.z for corner in face_corners_3d]

                    # Close the face by adding the first point at the end
                    face_x.append(face_x[0])
                    face_y.append(face_y[0])
                    face_z.append(face_z[0])

                    fig.add_trace(
                        go.Scatter3d(
                            x=face_x,
                            y=face_y,
                            z=face_z,
                            mode="lines+markers",
                            line={
                                "color": face_colors[i % len(face_colors)],
                                "width": 4,
                            },
                            marker={
                                "size": 6,
                                "color": face_colors[i % len(face_colors)],
                            },
                            name=f'Selected Face {i} ({face_data.get("face_name", "unknown")})',
                        )
                    )

        # Update layout
        fig.update_layout(
            title=f"3D Debug Visualization - Frame {frame_id}",
            scene={
                "xaxis_title": "X",
                "yaxis_title": "Y",
                "zaxis_title": "Z",
                "aspectmode": "data",
            },
            width=1000,
            height=800,
        )

        # Save as HTML file
        pyo.plot(fig, filename=output_path, auto_open=False)

    def generate_face_keypoints(self, face_data, cam_obj, sc):
        """
        Generate 6 keypoints for a pallet face: 4 corners of the 3D face + 2 middle points (top and bottom center).
        Uses the actual face corners and calculates middle points between them.
        """
        face_corners_3d = face_data["face_corners_3d"]

        # The face_corners_3d are ordered according to the face definition
        # Based on the face corner indices from detect_faces_in_scene:
        # Front face: [0, 1, 5, 4] - corners in order: bottom-left, bottom-right, top-right, top-left
        # Back face: [2, 3, 7, 6] - corners in order: bottom-left, bottom-right, top-right, top-left
        # Left face: [0, 3, 7, 4] - corners in order: bottom-left, bottom-right, top-right, top-left
        # Right face: [1, 2, 6, 5] - corners in order: bottom-left, bottom-right, top-right, top-left

        # Determine which corners are actually top/bottom based on Z coordinates
        # Sort corners by Z coordinate to find top and bottom pairs
        corners_with_z = [(corner, i) for i, corner in enumerate(face_corners_3d)]
        corners_with_z.sort(key=lambda x: x[0].z)

        # Bottom corners (lower Z)
        bottom_corners = [corners_with_z[0][0], corners_with_z[1][0]]

        # Top corners (higher Z)
        top_corners = [corners_with_z[2][0], corners_with_z[3][0]]

        # Sort bottom and top corners by X coordinate to get left/right
        bottom_corners.sort(key=lambda c: c.x)
        top_corners.sort(key=lambda c: c.x)

        bottom_left = bottom_corners[0]
        bottom_right = bottom_corners[1]
        top_left = top_corners[0]
        top_right = top_corners[1]

        # Calculate middle points as exact midpoints between corner pairs
        # Middle top: exact midpoint between top-left and top-right corners
        middle_top = (top_left + top_right) / 2
        # Middle bottom: exact midpoint between bottom-left and bottom-right corners
        middle_bottom = (bottom_left + bottom_right) / 2

        # Define 6 keypoints: 4 corners + 2 middle points
        keypoints_3d = [
            middle_top,  # 0: Middle top (center of top edge)
            middle_bottom,  # 1: Middle bottom (center of bottom edge)
            top_left,  # 2: Top left corner
            bottom_left,  # 3: Bottom left corner
            top_right,  # 4: Top right corner
            bottom_right,  # 5: Bottom right corner
        ]

        # Debug: Print keypoint information (commented out for production)
        # print(f"Generated 6 keypoints for {face_name} face:")
        # for i, kp in enumerate(keypoints_3d):
        #     print(f"  {i}: {['middle_top', 'middle_bottom', 'top_left', 'bottom_left', 'top_right', 'bottom_right'][i]} at {kp}")

        # Project keypoints to 2D and check visibility
        keypoints_2d = self.project_points(keypoints_3d, cam_obj, sc)

        # Check visibility for each keypoint
        keypoints_with_visibility = []
        for i, (kp_3d, kp_2d) in enumerate(
            zip(keypoints_3d, keypoints_2d, strict=False)
        ):
            # Check if keypoint is visible (not behind camera)
            visible = kp_2d[2] > 0

            # Additional visibility check: ray casting to see if there are obstacles
            if visible and self.config.get("keypoints_visibility_check", True):
                visible = self.check_keypoint_visibility(kp_3d, cam_obj, sc)

            keypoint_name = [
                "middle_top",
                "middle_bottom",
                "top_left",
                "bottom_left",
                "top_right",
                "bottom_right",
            ][i]

            # Debug: Print visibility information (commented out for production)
            # print(f"    {keypoint_name}: 2D=({kp_2d[0]:.1f}, {kp_2d[1]:.1f}), visible={visible}")

            keypoints_with_visibility.append(
                {
                    "id": i,
                    "name": keypoint_name,
                    "position_3d": [kp_3d.x, kp_3d.y, kp_3d.z],
                    "position_2d": [
                        kp_2d[0],
                        kp_2d[1],
                    ],  # Always use actual 2D coordinates
                    "visible": visible,
                    "depth": kp_2d[2] if visible else -1,
                }
            )

        return keypoints_with_visibility

    def check_keypoint_visibility(self, keypoint_3d, cam_obj, sc):
        """
        Check if a keypoint is visible by performing ray casting from camera to keypoint.
        Returns True if no obstacles are blocking the line of sight.
        """
        try:
            # Get camera location
            cam_location = cam_obj.location

            # Calculate direction from camera to keypoint
            direction = (keypoint_3d - cam_location).normalized()
            distance = (keypoint_3d - cam_location).length

            # Perform ray cast
            result, location, normal, index, object, matrix = sc.ray_cast(
                sc.view_layers[0].depsgraph, cam_location, direction, distance=distance
            )

            # If ray cast hits something before reaching the keypoint, it's occluded
            if result:
                # Check if the hit object is the face itself (allow self-intersection)
                return object and object.name.lower().find("face") != -1

            return True

        except Exception as e:
            logger.error(f"Error checking keypoint visibility: {e}")
            return True  # Default to visible if check fails

    def save_keypoints_labels(self, keypoints_data, frame_id, img_w, img_h):
        """
        Save keypoints labels in YOLO format to the keypoints_labels folder.
        Format: class_id x_center y_center width height kp1_x kp1_y kp1_v kp2_x kp2_y kp2_v ...
        """
        if not keypoints_data:
            return

        keypoints_file = os.path.join(self.paths["keypoints"], f"{frame_id:06d}.txt")

        with open(keypoints_file, "w") as f:
            for face_data in keypoints_data:
                face_bbox = face_data["bbox_2d"]
                keypoints = face_data["keypoints"]

                # Convert bbox to YOLO format (normalized)
                x_center = (face_bbox["x_min"] + face_bbox["x_max"]) / 2 / img_w
                y_center = (face_bbox["y_min"] + face_bbox["y_max"]) / 2 / img_h
                width = face_bbox["width"] / img_w
                height = face_bbox["height"] / img_h

                # Write class_id (assuming face is class 0)
                line = f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"

                # Add keypoints (normalized coordinates and visibility)
                for kp in keypoints:
                    # Always use actual 2D coordinates, regardless of visibility
                    kp_x = kp["position_2d"][0] / img_w
                    kp_y = kp["position_2d"][1] / img_h
                    visibility = (
                        2 if kp["visible"] else 0
                    )  # 2 = visible, 0 = not visible
                    line += f" {kp_x:.6f} {kp_y:.6f} {visibility}"

                f.write(line + "\n")
