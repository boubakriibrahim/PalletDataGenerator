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
    print("▶", " ".join(cmd))
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

print("Pillow available:", PIL_AVAILABLE)


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
            print("[floor] Specular socket not found; skipping.")

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
    ):
        """
        Create analysis image with 2D/3D bounding boxes, holes, and legend.
        Exact copy from original one_pallet_generator.py
        """

        if not PIL_AVAILABLE:
            return False
        try:
            import os

            if not os.path.exists(rgb_path):
                return False

            img = Image.open(rgb_path).convert("RGB")
            draw = ImageDraw.Draw(img)
            font_size = max(16, min(32, img.width // 40))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

            color_2d = (0, 255, 0)
            color_3d = (255, 0, 0)
            color_hole = (0, 128, 255)
            color_text = (255, 255, 255)

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

            # Draw legend
            pad, sample_sz, line_gap = 8, 18, 8
            legend_items = [
                (f"Frame {frame_id}", None),
                ("2D bbox", color_2d),
                ("3D bbox", color_3d),
                ("Hole polygon", color_hole),
            ]
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
            print(f"[DEBUG] Analysis image saved successfully to: {output_path}")

            # Verify the file was actually created
            import os

            if os.path.exists(output_path):
                _file_size = os.path.getsize(output_path)

            else:
                return False

            return True
        except Exception as e:
            print(f"Analysis overlay error: {e}")
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
        """Basic auto-exposure adjustment."""
        # Simplified version - just return a reasonable EV value
        # Real implementation would measure luminance and adjust accordingly
        cfg = self.config
        if cfg.get("enable_auto_exposure", True):
            # Set a reasonable exposure value
            target_ev = cfg.get("initial_exposure_ev", 0.0)
            sc.view_settings.exposure = target_ev
            return target_ev
        return 0.0
