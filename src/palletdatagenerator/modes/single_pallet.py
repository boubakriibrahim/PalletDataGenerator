"""
Single Pallet Mode - Based on original one_pallet_generator.py

Implements the exact camera positioning, movement, and generation logic
from the original single pallet generator.
"""

import contextlib
import json
import math
import os
import random
import sys

import bpy
from mathutils import Euler, Matrix, Vector

from .base_generator import BaseGenerator

try:
    from pascal_voc_writer import Writer as VocWriter
except ImportError:
    VocWriter = None


class SinglePalletMode(BaseGenerator):
    """
    Single pallet generation mode with camera movement around a stationary pallet.
    Replicates the exact behavior of the original one_pallet_generator.py
    """

    def __init__(self, config):
        super().__init__(config)
        self.mode_name = "single_pallet"

    def position_camera_for_side_face(self, cam_obj, target_obj, cfg):
        """
        Position camera to focus on side faces of the pallet, EXACT as in original.
        Includes ground-safe positioning to prevent camera going below floor.
        """
        tp = Vector(target_obj.location)
        ground_z = self._get_ground_z()
        z_margin = float(cfg.get("camera_min_z_above_ground", 0.05))
        min_allowed_z = ground_z + z_margin

        az = el = dist = None
        cam_pos = None
        for _ in range(10):
            if random.random() < cfg.get("side_face_probability", 0.9):
                face_angles = cfg["preferred_face_angles"]
                chosen_face = random.choice(list(face_angles.keys()))
                angle_range = face_angles[chosen_face]
                az = math.radians(random.uniform(angle_range[0], angle_range[1]))
                el = math.radians(random.uniform(0, 30))
                dist = random.uniform(2.0, 3.5)
            else:
                az = math.radians(random.uniform(0, 360))
                el = math.radians(random.uniform(-5, 35))
                dist = random.uniform(1.8, 4.0)

            candidate = tp + Vector(
                (
                    dist * math.cos(az) * math.cos(el),
                    dist * math.sin(az) * math.cos(el),
                    dist * math.sin(el),
                )
            )
            if candidate.z >= min_allowed_z:
                cam_pos = candidate
                break
        if cam_pos is None:
            cam_pos = candidate
        if cam_pos.z < min_allowed_z:
            cam_pos.z = min_allowed_z

        cam_obj.location = cam_pos
        look_dir = (tp + Vector((0, 0, 0.1)) - cam_pos).normalized()
        cam_obj.rotation_euler = look_dir.to_track_quat("-Z", "Y").to_euler()
        return {
            "azimuth": math.degrees(az),
            "elevation": math.degrees(el),
            "distance": dist,
            "camera_z": cam_pos.z,
            "ground_z": ground_z,
        }

    def _get_ground_z(self):
        """Get the Z coordinate of the floor/ground - uses base class implementation."""
        return super()._get_ground_z()

    def generate_frames(self):
        """
        Main generation loop exactly as in original one_pallet_generator.py
        """
        print("🚀 Starting single pallet generation...")
        import sys

        sys.stdout.flush()

        # Setup output folders first
        self.setup_folders()
        print("📁 Output folders created")
        sys.stdout.flush()

        # Get the main pallet object
        base = bpy.data.objects.get("pallet")
        if not base or base.type != "MESH":
            raise RuntimeError("Object 'pallet' not found or is not a mesh.")

        # Setup camera
        cam_data = bpy.data.cameras.new("SynthCam")
        cam_obj = bpy.data.objects.new("SynthCam", cam_data)
        bpy.context.collection.objects.link(cam_obj)
        cam_obj.data.lens = self.config["camera_focal_mm"]
        cam_obj.data.sensor_width = self.config["camera_sensor_mm"]
        bpy.context.scene.camera = cam_obj

        # Setup environment
        self.setup_environment()
        self.setup_lighting(base)

        # Prepare pallets
        pallets = self.prepare_pallets(base)

        # COCO scaffolding
        coco = {
            "info": {},
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": [
                {"id": 1, "name": base.name, "supercategory": "object"},
                {"id": 2, "name": "hole", "supercategory": "pocket"},
            ],
        }
        ann_id = 1
        meta = []
        valid = 0
        total = self.config["num_images"]
        _img_w, _img_h = self.config["resolution_x"], self.config["resolution_y"]
        sc = bpy.context.scene

        # Save scene before rendering (if enabled)
        if self.config.get("save_scene_before_render", False):
            self.save_generated_scene()

        print(f"🔄 Starting generation loop: {total} frames")

        # Main generation loop - exactly as in original
        while valid < total:
            sc.frame_current = valid

            # Optional per-frame XY shift for pallet movement
            if self.config.get("allow_pallet_move_xy", False):
                self.apply_pallet_movement(pallets)

            # Re-roll lights per frame (optional)
            if self.config.get("randomize_lights_per_frame", False):
                self.create_random_lights(pallets[0], replace_existing=True)

            # Camera movement - the key difference from current implementation!
            focus_obj = pallets[min(len(pallets) // 2, len(pallets) - 1)]
            _camera_info = self.position_camera_for_side_face(
                cam_obj, focus_obj, self.config
            )

            # Handle attached boxes (per-frame rebuilding)
            self.handle_attached_boxes(pallets)

            # Get detections for all visible pallets
            b2d_list, b3d_list, pockets_list = self.get_detections(pallets, cam_obj, sc)

            if not b2d_list:
                print(f"[skip] frame {valid} - no visible pallets")
                valid += 1
                continue

            # Auto exposure
            _new_ev = self.auto_expose_frame(sc, cam_obj)

            # Render final image
            fn = f"{valid:06d}"
            img_path = os.path.join(self.paths["images"], f"{fn}.png")
            sc.render.filepath = img_path
            sc.render.image_settings.file_format = "PNG"
            bpy.ops.render.render(write_still=True)

            # Generate all outputs (analysis, annotations, etc.)
            ann_id = self.save_frame(
                img_path,
                b2d_list,
                b3d_list,
                pockets_list,
                cam_obj,
                sc,
                valid,
                fn,
                coco,
                ann_id,
                meta,
                pallets,
            )

            print(
                f"✅ [{valid+1}/{total}] frame {fn} - {len(b2d_list)} pallets visible; EV={sc.view_settings.exposure:+.2f}"
            )
            valid += 1

        print(f"🎉 Generation completed! Generated {valid} frames")

        # Write final outputs
        self.save_final_outputs(coco, meta)

        return {
            "frames_generated": valid,
            "output_dir": self.config["output_dir"],
            "mode": self.mode_name,
        }

    def apply_pallet_movement(self, pallets):
        """Apply optional XY movement to pallets while keeping vertical stack."""
        cfg = self.config
        base_mat = pallets[0].matrix_world.copy()  # Get original transform

        tx = random.uniform(*cfg["pallet_move_x_range"])
        ty = random.uniform(*cfg["pallet_move_y_range"])
        delta = Matrix.Translation(Vector((tx, ty, 0.0)))

        for idx, po in enumerate(pallets):
            # Calculate vertical offset for stacked pallets
            z_off = (
                idx
                * (pallets[0].dimensions.z + float(cfg.get("pallet_stack_gap", 0.05)))
                if cfg.get("duplicate_pallets", False)
                and cfg.get("pallet_stack_vertical", True)
                else 0.0
            )
            base_stack = base_mat.copy()
            base_stack.translation.z += z_off
            po.matrix_world = base_stack @ delta

    def prepare_pallets(self, base):
        """Prepare pallet objects (duplicates, materials, etc.) exactly as original."""
        # Store original matrix
        base_mat = base.matrix_world.copy()

        # Create duplicates if needed
        pallets = self.duplicate_pallets_if_needed(base)

        # Set pass indices for object identification
        if self.config.get("unique_object_index", True):
            for i, po in enumerate(pallets, start=1):
                po.pass_index = i
        else:
            for po in pallets:
                po.pass_index = 1

        # Apply materials
        for po in pallets:
            self.randomize_object_material(po)

        # Apply initial transform if requested
        if self.config.get("apply_initial_random_transform", False):
            self.apply_initial_transform(pallets, base_mat)
        else:
            # Just position pallets according to stacking rules
            self.position_pallets(pallets, base_mat)

        return pallets

    def duplicate_pallets_if_needed(self, base_obj):
        """Create duplicate pallets if requested in config."""
        pallets = [base_obj]
        if not self.config.get("duplicate_pallets", False):
            return pallets

        n = max(1, int(self.config.get("num_pallets", 1)))
        if n <= 1:
            return pallets

        base_h = base_obj.dimensions.z
        gap = float(self.config.get("pallet_stack_gap", 0.05))

        for i in range(1, n):
            dup = base_obj.copy()
            dup.data = base_obj.data
            dup.name = f"{base_obj.name}_{i}"
            bpy.context.collection.objects.link(dup)

            if self.config.get("pallet_stack_vertical", True):
                dup.matrix_world = base_obj.matrix_world.copy()
                dup.location.z = base_obj.location.z + i * (base_h + gap)
            else:
                dup.matrix_world = base_obj.matrix_world.copy()
                dup.location.x += (i % 2) * (base_obj.dimensions.x + 0.1)
                dup.location.y += (i // 2) * (base_obj.dimensions.y + 0.1)

            pallets.append(dup)

        return pallets

    def position_pallets(self, pallets, base_mat):
        """Position pallets according to stacking configuration."""
        for idx, po in enumerate(pallets):
            z_off = (
                idx
                * (
                    pallets[0].dimensions.z
                    + float(self.config.get("pallet_stack_gap", 0.05))
                )
                if self.config.get("duplicate_pallets", False)
                and self.config.get("pallet_stack_vertical", True)
                else 0.0
            )
            base_stack = base_mat.copy()
            base_stack.translation.z += z_off
            po.matrix_world = base_stack

    def setup_lighting(self, base_obj):
        """Setup lighting system."""
        # Create initial lights
        self.create_random_lights(base_obj, replace_existing=True)

    def create_random_lights(self, anchor_obj, replace_existing=False):
        """Create random lighting around the anchor object - uses base class method."""
        return super().create_random_lights(anchor_obj, replace_existing)

    def handle_attached_boxes(self, pallets):
        """Handle attached box variants per frame - EXACT from original."""
        cfg = self.config
        if cfg.get("attached_box_name"):
            self._cleanup_attached_group()

            # Check if placeholder exists
            placeholder = bpy.data.objects.get(cfg.get("attached_box_name"))

            if placeholder:
                # Hide placeholder if configured
                if cfg.get("hide_placeholder_box", True):
                    placeholder.hide_render = True
                    placeholder.hide_viewport = True

                # build group/single fresh each frame (if enabled)
                if cfg.get("attached_box_group", False):
                    self._build_attached_box_group(cfg, placeholder, pallets[0])
                else:
                    self._build_attached_box_single(cfg, placeholder, pallets[0])

    # Attached box system constants and functions (EXACT from original)
    ATTACHED_GROUP_PREFIX = "AttachedGroup_"

    def _cleanup_attached_group(self):
        """Clean up existing attached group objects."""
        to_remove = [
            o for o in bpy.data.objects if o.name.startswith(self.ATTACHED_GROUP_PREFIX)
        ]
        for o in to_remove:
            with contextlib.suppress(Exception):
                bpy.data.objects.remove(o, do_unlink=True)

    def _scale_object_to_bbox(self, obj, target_dims):
        """Scale object to match target dimensions."""
        try:
            cur = obj.dimensions
            sx = target_dims[0] / cur.x if cur.x else 1.0
            sy = target_dims[1] / cur.y if cur.y else 1.0
            sz = target_dims[2] / cur.z if cur.z else 1.0
            obj.scale.x *= sx
            obj.scale.y *= sy
            obj.scale.z *= sz
        except Exception:
            pass

    def _bottom_world_z(self, obj):
        """Get bottom Z coordinate of object in world space."""
        with contextlib.suppress(Exception):
            bpy.context.view_layer.update()
        try:
            corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            return min(c.z for c in corners)
        except Exception:
            return obj.location.z

    def _align_bottom(self, obj, target_bottom_z):
        """Align object's bottom to target Z coordinate."""
        cur_bottom = self._bottom_world_z(obj)
        dz = target_bottom_z - cur_bottom
        if abs(dz) > 1e-6:
            obj.location.z += dz

    def _build_attached_box_single(self, cfg, placeholder, pallet):
        """Build single attached box - EXACT from original."""
        variants = [
            v for v in cfg.get("attached_box_variants", []) if bpy.data.objects.get(v)
        ]
        if not variants:
            return
        name_src = random.choice(variants)
        src = bpy.data.objects.get(name_src)
        if not src:
            return
        dup = src.copy()
        dup.data = src.data
        dup.name = self.ATTACHED_GROUP_PREFIX + name_src
        bpy.context.collection.objects.link(dup)
        dup.matrix_world = placeholder.matrix_world.copy()
        self._scale_object_to_bbox(dup, placeholder.dimensions)
        ph_bottom = self._bottom_world_z(placeholder)
        self._align_bottom(dup, ph_bottom)
        dup.parent = pallet
        with contextlib.suppress(Exception):
            dup.matrix_parent_inverse = pallet.matrix_world.inverted()

    def _build_attached_box_group(self, cfg, placeholder, pallet):
        """Build group of attached boxes - EXACT from original."""
        variants = [
            v for v in cfg.get("attached_box_variants", []) if bpy.data.objects.get(v)
        ]
        if not variants:
            return

        bpy.context.view_layer.update()
        pallet_corners = [pallet.matrix_world @ Vector(c) for c in pallet.bound_box]
        pallet_min_x = min(c.x for c in pallet_corners)
        pallet_max_x = max(c.x for c in pallet_corners)
        pallet_min_y = min(c.y for c in pallet_corners)
        pallet_max_y = max(c.y for c in pallet_corners)
        pallet_max_z = max(c.z for c in pallet_corners)

        target_width = pallet_max_x - pallet_min_x
        target_depth = pallet_max_y - pallet_min_y

        ph_matrix = placeholder.matrix_world
        ph_corners = [ph_matrix @ Vector(c) for c in placeholder.bound_box]
        ph_min_z = min(c.z for c in ph_corners)
        ph_max_z = max(c.z for c in ph_corners)
        base_height = ph_max_z - ph_min_z

        extra_h_min, extra_h_max = cfg.get(
            "attached_box_allow_extra_height", (1.0, 1.2)
        )
        max_height = base_height * random.uniform(extra_h_min, extra_h_max)

        count = random.randint(*cfg.get("attached_box_group_count_range", (2, 3)))

        # Find best grid layout
        best_grid = None
        best_aspect = float("inf")
        for rows in range(1, count + 1):
            cols = max(1, (count + rows - 1) // rows)
            if rows * cols >= count:
                grid_aspect = max(rows / cols, cols / rows)
                if grid_aspect < best_aspect:
                    best_aspect = grid_aspect
                    best_grid = (rows, cols)
        if not best_grid:
            best_grid = (1, count)
        grid_rows, grid_cols = best_grid

        cell_width = target_width / grid_cols
        cell_depth = target_depth / grid_rows

        enable_stacking = cfg.get("attached_box_enable_stacking", True)
        stack_prob = cfg.get("attached_box_stack_probability", 0.6)
        stack_range = cfg.get("attached_box_stack_layers_range", (2, 4))
        offset_factor = cfg.get("attached_box_stack_offset_factor", 0.05)

        created_objects = []
        obj_index = 0

        for row in range(grid_rows):
            for col in range(grid_cols):
                if obj_index >= count:
                    break

                cell_min_x = pallet_min_x + col * cell_width
                cell_max_x = pallet_min_x + (col + 1) * cell_width
                cell_min_y = pallet_min_y + row * cell_depth
                cell_max_y = pallet_min_y + (row + 1) * cell_depth

                cell_center_x = (cell_min_x + cell_max_x) / 2.0
                cell_center_y = (cell_min_y + cell_max_y) / 2.0

                create_stack = enable_stacking and random.random() < stack_prob
                stack_layers = random.randint(*stack_range) if create_stack else 1

                cell_objects = []
                for layer in range(stack_layers):
                    src_name = random.choice(variants)
                    src = bpy.data.objects.get(src_name)
                    if not src:
                        continue

                    dup = src.copy()
                    dup.data = src.data
                    dup.name = (
                        f"{self.ATTACHED_GROUP_PREFIX}{obj_index}_{layer}_{src_name}"
                    )
                    bpy.context.collection.objects.link(dup)

                    dup.matrix_world = Matrix.Identity(4)
                    bpy.context.view_layer.update()

                    src_corners = [Vector(c) for c in src.bound_box]
                    src_min_x = min(c.x for c in src_corners)
                    src_max_x = max(c.x for c in src_corners)
                    src_min_y = min(c.y for c in src_corners)
                    src_max_y = max(c.y for c in src_corners)
                    src_min_z = min(c.z for c in src_corners)
                    src_max_z = max(c.z for c in src_corners)

                    src_width = max(1e-6, src_max_x - src_min_x)
                    src_depth = max(1e-6, src_max_y - src_min_y)
                    src_height = max(1e-6, src_max_z - src_min_z)

                    scale_x = cell_width / src_width
                    scale_y = cell_depth / src_depth

                    if layer == 0:
                        target_obj_height = max_height * random.uniform(0.5, 0.8)
                    else:
                        target_obj_height = max_height * random.uniform(0.3, 0.6)
                    scale_z = target_obj_height / src_height

                    dup.scale = Vector((scale_x, scale_y, scale_z))
                    bpy.context.view_layer.update()

                    if layer == 0:
                        target_x = cell_center_x
                        target_y = cell_center_y
                        target_z = pallet_max_z
                    else:
                        max_offset_x = cell_width * offset_factor * 0.5
                        max_offset_y = cell_depth * offset_factor * 0.5
                        offset_x = random.uniform(-max_offset_x, max_offset_x)
                        offset_y = random.uniform(-max_offset_y, max_offset_y)
                        target_x = cell_center_x + offset_x
                        target_y = cell_center_y + offset_y
                        prev_obj = cell_objects[-1]
                        prev_corners = [
                            prev_obj.matrix_world @ Vector(c)
                            for c in prev_obj.bound_box
                        ]
                        prev_top_z = max(c.z for c in prev_corners)
                        stack_gap = random.uniform(0, cell_width * offset_factor * 0.2)
                        target_z = prev_top_z + stack_gap

                    dup_corners = [dup.matrix_world @ Vector(c) for c in dup.bound_box]
                    dup_center_x = (
                        min(c.x for c in dup_corners) + max(c.x for c in dup_corners)
                    ) / 2.0
                    dup_center_y = (
                        min(c.y for c in dup_corners) + max(c.y for c in dup_corners)
                    ) / 2.0
                    dup_min_z = min(c.z for c in dup_corners)

                    final_x = target_x - dup_center_x
                    final_y = target_y - dup_center_y
                    final_z = target_z - dup_min_z

                    dup.location = Vector((final_x, final_y, final_z))
                    bpy.context.view_layer.update()

                    dup.parent = pallet
                    with contextlib.suppress(Exception):
                        dup.matrix_parent_inverse = pallet.matrix_world.inverted()

                    created_objects.append(dup)
                    cell_objects.append(dup)

                obj_index += 1
                if obj_index >= count:
                    break

    def get_detections(self, pallets, cam_obj, sc):
        """Get 2D and 3D bounding boxes for all visible pallets - EXACT from original."""
        b2d_list = []
        b3d_list = []
        pockets_list = []

        for po in pallets:
            b2d = self.get_bbox_2d_accurate(po, cam_obj, sc)
            if not b2d:  # off-screen or behind camera
                continue

            cfg = self.config
            if cfg.get("allow_cropping", False):
                if (
                    b2d["visible_ratio"] < cfg.get("min_visible_area_ratio", 0.3)
                    or b2d["crop_ratio"] > cfg.get("max_crop_ratio", 0.7)
                    or b2d["area"] < 50
                ):
                    continue
            else:
                if b2d["area"] < 100:
                    continue

            b2d_list.append(b2d)
            b3d_list.append(self.bbox_3d_oriented(po))
            pockets_list.append(self.hole_bboxes_3d(po))

        return b2d_list, b3d_list, pockets_list

    def auto_expose_frame(self, sc, cam_obj):
        """Auto-exposure adjustment for the frame - uses base class method."""
        return super().auto_expose_frame(sc, cam_obj)

    def save_frame(
        self,
        img_path,
        b2d_list,
        b3d_list,
        pockets_list,
        cam_obj,
        sc,
        valid,
        fn,
        coco,
        ann_id,
        meta,
        pallets,
    ):
        """Save all outputs for a single frame: analysis, YOLO, VOC, COCO, metadata - EXACT from original."""

        # Helper functions for coordinate conversion - EXACT from original pattern
        def xyxy_to_xywh(b2d):
            """Convert bbox from x_min,y_min,x_max,y_max to x,y,width,height for COCO"""
            return [b2d["x_min"], b2d["y_min"], b2d["width"], b2d["height"]]

        def xyxy_to_yolo(b2d, img_w, img_h):
            """Convert bbox to YOLO format: center_x, center_y, width, height (normalized)"""
            x_center = (b2d["x_min"] + b2d["x_max"]) / 2 / img_w
            y_center = (b2d["y_min"] + b2d["y_max"]) / 2 / img_h
            width = b2d["width"] / img_w
            height = b2d["height"] / img_h
            return x_center, y_center, width, height

        # Generate analysis image - ALWAYS generate like original (no config check)
        ana_path = None
        try:
            import PIL.Image  # noqa: F401
            import PIL.ImageDraw  # noqa: F401
            import PIL.ImageFont  # noqa: F401

            PIL_AVAILABLE = True
        except ImportError:
            PIL_AVAILABLE = False
            print("⚠️  PIL not available - skipping analysis image")

        if PIL_AVAILABLE:
            ana_path = os.path.join(self.paths["analysis"], f"analysis_{fn}.png")

            # Ensure analysis directory exists
            os.makedirs(self.paths["analysis"], exist_ok=True)

            try:
                success = self.create_analysis_image_multi(
                    img_path,
                    b2d_list,
                    b3d_list,
                    pockets_list,
                    cam_obj,
                    sc,
                    ana_path,
                    valid,
                )
                if success:
                    print(f"📊 Analysis image saved: analysis_{fn}.png")
                    sys.stdout.flush()
                else:
                    print(f"⚠️  Analysis image creation failed for frame {valid}")
            except Exception as e:
                print(f"❌ Analysis image error: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("⚠️  Skipping analysis generation - PIL not available")

        # COCO (image)
        img_w, img_h = self.config["resolution_x"], self.config["resolution_y"]
        coco["images"].append(
            {"id": valid, "file_name": f"{fn}.png", "width": img_w, "height": img_h}
        )

        # YOLO pallets (class 0) - EXACT from original
        yolo_file = os.path.join(self.paths["yolo"], f"{fn}.txt")
        with open(yolo_file, "w") as y:
            pass
        for b2d in b2d_list:
            coco["annotations"].append(
                {
                    "id": ann_id,
                    "image_id": valid,
                    "category_id": 1,
                    "bbox": xyxy_to_xywh(b2d),
                    "area": b2d["area"],
                    "iscrowd": 0,
                    "segmentation": [],
                }
            )
            ann_id += 1
            xc, yc, w, h = xyxy_to_yolo(b2d, img_w, img_h)
            with open(yolo_file, "a") as y:
                y.write(f"0 {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")

        # Holes (class 1) - using exact original logic
        for pockets in pockets_list:
            ann_id = self.project_holes_and_write_labels(
                pockets, cam_obj, sc, self.paths["yolo"], fn, coco, ann_id, img_w, img_h
            )

        # VOC (all pallets) - EXACT from original
        if PIL_AVAILABLE:
            try:
                from pascal_voc_writer import Writer as VocWriter

                voc = VocWriter(img_path, img_w, img_h)
                for b2d in b2d_list:
                    voc.addObject(
                        "pallet",  # Use original object name
                        int(b2d["x_min"]),
                        int(b2d["y_min"]),
                        int(b2d["x_max"]),
                        int(b2d["y_max"]),
                    )
                voc.save(os.path.join(self.paths["voc"], f"{fn}.xml"))
            except Exception:
                pass

        # Metadata - EXACT from original format
        meta.append(
            {
                "frame": valid,
                "image_id": fn,
                "rgb": img_path,
                "analysis_png": ana_path,
                "boxes_2d": len(b2d_list),
                "boxes_3d": len(b3d_list),
                "pockets": len(pockets_list),
                "pallets": [
                    {
                        "name": po.name,
                        "position": list(po.location),
                        "rotation": list(po.rotation_euler),
                        "scale": list(po.scale),
                        "pass_index": po.pass_index,
                    }
                    for po in pallets
                ],
            }
        )

        return ann_id

    def project_holes_and_write_labels(
        self,
        pockets_world,
        cam,
        sc,
        yolo_dir,
        img_idx,
        coco,
        ann_id_start,
        img_w,
        img_h,
    ):
        """Project holes and write YOLO/COCO labels - EXACT from original."""
        ann_id = ann_id_start
        yolo_lines = []
        for pk in pockets_world:
            proj = self.project_points(pk, cam, sc)
            vis = [p for p in proj if p[2] > 0]
            if len(vis) < 4:
                continue
            xs, ys = zip(*[(p[0], p[1]) for p in vis], strict=False)
            x0, y0 = max(0, min(xs)), max(0, min(ys))
            x1, y1 = min(img_w, max(xs)), min(img_h, max(ys))
            w, h = x1 - x0, y1 - y0
            if w < 2 or h < 2:
                continue
            xc = (x0 + x1) / 2 / img_w
            yc = (y0 + y1) / 2 / img_h
            yolo_lines.append(f"1 {xc:.6f} {yc:.6f} {w/img_w:.6f} {h/img_h:.6f}")
            poly = [coord for p in vis for coord in (p[0], p[1])]
            coco["annotations"].append(
                {
                    "id": ann_id,
                    "image_id": int(img_idx),
                    "category_id": 2,
                    "bbox": [x0, y0, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                    "segmentation": [poly],
                }
            )
            ann_id += 1
        if yolo_lines:
            with open(os.path.join(yolo_dir, f"{img_idx}.txt"), "a") as f:
                f.write("\n".join(yolo_lines) + "\n")
        return ann_id

    def save_final_outputs(self, coco, meta):
        """Save final COCO and metadata files."""
        root = self.config["output_dir"]

        with open(os.path.join(root, "annotations_coco.json"), "w") as jf:
            json.dump(coco, jf, indent=2)

        with open(os.path.join(root, "dataset_manifest.json"), "w") as mf:
            json.dump({"config": self.config, "frames": meta}, mf, indent=2)

        print("✅ COCO / YOLO / VOC annotations written.")

    def apply_initial_transform(self, pallets, base_mat):
        """Apply random initial transform to pallets."""
        t = Matrix.Translation(
            Vector(
                (
                    random.uniform(-0.1, 0.1),
                    random.uniform(-0.1, 0.1),
                    random.uniform(-0.05, 0.05),
                )
            )
        )
        r = (
            Euler(
                (
                    math.radians(random.uniform(-10, 10)),
                    math.radians(random.uniform(-10, 10)),
                    math.radians(random.uniform(-45, 45)),
                )
            )
            .to_matrix()
            .to_4x4()
        )
        s = Matrix.Scale(random.uniform(0.8, 1.2), 4)
        delta = t @ r @ s

        for idx, po in enumerate(pallets):
            z_off = (
                idx
                * (
                    pallets[0].dimensions.z
                    + float(self.config.get("pallet_stack_gap", 0.05))
                )
                if self.config.get("duplicate_pallets", False)
                and self.config.get("pallet_stack_vertical", True)
                else 0.0
            )
            base_stack = base_mat.copy()
            base_stack.translation.z += z_off
            po.matrix_world = base_stack @ delta

    def save_generated_scene(self):
        """
        Save the current generated scene to a .blend file in the scenes folder.
        This allows inspection and reuse of the randomized single pallet layout.
        """
        import os
        from pathlib import Path

        # Create scenes folder if it doesn't exist
        scenes_folder = Path("scenes")
        scenes_folder.mkdir(exist_ok=True)

        # Generate scene filename with batch info
        batch_name = os.path.basename(self.paths.get("root", "unknown_batch"))
        scene_filename = f"single_pallet_generated_{batch_name}.blend"
        scene_path = scenes_folder / scene_filename

        try:
            print(f"💾 Saving generated scene to: {scene_path}")
            import sys

            sys.stdout.flush()
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
            print(f"✅ Scene saved successfully: {scene_filename}")
            sys.stdout.flush()

            # Also save scene info as JSON for reference
            scene_info = {
                "mode": "single_pallet",
                "batch_folder": batch_name,
                "config_used": {
                    "num_images": self.config.get("num_images", "unknown"),
                    "duplicate_pallets": self.config.get("duplicate_pallets", False),
                    "num_pallets": self.config.get("num_pallets", 1),
                    "pallet_stack_vertical": self.config.get(
                        "pallet_stack_vertical", True
                    ),
                    "allow_pallet_move_xy": self.config.get(
                        "allow_pallet_move_xy", False
                    ),
                },
                "timestamp": str(__import__("datetime").datetime.now()),
            }

            info_path = scenes_folder / f"single_pallet_{batch_name}_info.json"
            with open(info_path, "w") as f:
                import json

                json.dump(scene_info, f, indent=2)

        except Exception as e:
            print(f"⚠️  Failed to save generated scene: {e}")
            import sys

            sys.stdout.flush()
