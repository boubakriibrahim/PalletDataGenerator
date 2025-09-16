"""
Warehouse Mode - Based on original warehouse_generator.py

Implements the exact forklift simulation, camera paths, and generation logic
from the original warehouse generator.
"""

import contextlib
import math
import os
import random

import bpy
import numpy as np
from mathutils import Euler, Vector

from .base_generator import BaseGenerator

try:
    from pascal_voc_writer import Writer as VocWriter
except ImportError:
    VocWriter = None


class WarehouseMode(BaseGenerator):
    """
    Warehouse generation mode with forklift simulation and camera paths.
    Replicates the exact behavior of the original warehouse_generator.py
    """

    def __init__(self, config):
        super().__init__(config)
        self.mode_name = "warehouse"
        self.attached_group_prefix = "AttachedGroup_"

    def generate_frames(self):
        """
        Main warehouse generation loop exactly as in original warehouse_generator.py
        """
        print("🏭 Starting warehouse generation...")
        import sys

        sys.stdout.flush()

        # Initialization
        random.seed()
        np.random.seed()

        # Setup camera
        sc = bpy.context.scene
        if sc.camera:
            with contextlib.suppress(Exception):
                bpy.data.objects.remove(sc.camera, do_unlink=True)

        cam_data = bpy.data.cameras.new("WarehouseCam")
        cam_obj = bpy.data.objects.new("WarehouseCam", cam_data)
        bpy.context.collection.objects.link(cam_obj)
        cam_obj.data.lens = self.config["camera_focal_mm"]
        cam_obj.data.sensor_width = self.config["camera_sensor_mm"]
        sc.camera = cam_obj

        # Setup environment
        self.setup_environment()

        # Analyze scene
        print("🔍 Analyzing warehouse scene...")
        scene_objects = self.find_warehouse_objects()

        if not scene_objects["pallets"]:
            print("⚠️  WARNING: No pallets found!")
            print("Check that your objects contain 'pallet' in their name")
            return {"frames_generated": 0, "error": "No pallets found"}

        # COCO scaffolding
        coco_data = {
            "info": {"description": "Warehouse Realistic Dataset"},
            "licenses": [],
            "images": [],
            "annotations": [],
            "categories": [
                {"id": 1, "name": "pallet", "supercategory": "object"},
                {"id": 2, "name": "face", "supercategory": "pallet_part"},
                {"id": 3, "name": "hole", "supercategory": "pallet_part"},
            ],
        }

        total_images = 0
        meta = []

        # Main generation loop - multiple scenes
        for scene_id in range(self.config["num_scenes"]):
            print(f"\n--- SCENE {scene_id + 1}/{self.config['num_scenes']} ---")

            # Clean up previously generated boxes
            self.cleanup_generated_boxes()

            # Randomize scene
            (
                removed_objects,
                modified_objects,
                original_positions,
            ) = self.randomize_scene_objects(scene_objects)

            # Re-scan objects after adding groups
            print("🔄 Re-scanning objects after group placement...")
            scene_objects["pallet_box_groups"] = self.find_pallet_box_relationships(
                scene_objects
            )

            # Force complete update
            bpy.context.view_layer.update()
            bpy.context.evaluated_depsgraph_get().update()

            # Generate warehouse camera path (forklift simulation)
            camera_path = self.generate_warehouse_path(scene_objects)

            # Save scene before rendering (if enabled)
            if self.config.get("save_scene_before_render", False):
                self.save_generated_scene(scene_id)

            # Images for this scene
            scene_images = min(
                self.config["max_images_per_scene"],
                self.config["max_total_images"] - total_images,
            )

            # Generate images along the path
            for img_id in range(scene_images):
                frame_id = total_images

                print(
                    f"📸 Rendering frame {frame_id + 1}/{self.config['max_total_images']} (Scene {scene_id + 1}, Image {img_id + 1}/{scene_images})"
                )
                import sys

                sys.stdout.flush()

                # Position camera with forklift-like movement
                progress = img_id / max(1, scene_images - 1)
                self.position_camera_on_path(cam_obj, camera_path, progress)

                # Dynamic lighting
                self.randomize_lighting()

                # Auto-exposure
                self.auto_expose_frame(sc, cam_obj)

                # Detect visible pallets
                visible_pallets = self.get_visible_pallets(scene_objects, cam_obj, sc)

                if not visible_pallets:
                    print("    No pallets visible")
                    continue

                # Render
                img_filename = f"{frame_id:06d}.png"
                img_path = os.path.join(self.paths["images"], img_filename)
                sc.render.filepath = img_path
                sc.render.image_settings.file_format = "PNG"

                try:
                    bpy.ops.render.render(write_still=True)
                    print(f"    ✅ {img_filename} - {len(visible_pallets)} pallets")
                except Exception as e:
                    print(f"    ❌ Render error: {e}")
                    continue

                # Generate all outputs
                self.save_warehouse_frame_outputs(
                    frame_id,
                    img_filename,
                    img_path,
                    visible_pallets,
                    cam_obj,
                    sc,
                    coco_data,
                    meta,
                )

                total_images += 1

                if total_images >= self.config["max_total_images"]:
                    break

            # Restore scene
            self.restore_scene_objects(removed_objects, original_positions)

            if total_images >= self.config["max_total_images"]:
                break

        # Save final outputs
        self.save_final_outputs(coco_data, meta)

        print("\n🎉 WAREHOUSE DATASET GENERATED!")
        print(f"📊 Images generated: {total_images}")
        print(f"📁 Output: {self.config['output_dir']}")

        return {
            "frames_generated": total_images,
            "output_dir": self.config["output_dir"],
            "mode": self.mode_name,
        }

    def find_warehouse_objects(self):
        """Find and categorize warehouse objects by collections (object.XXX structure)."""
        objects = {"pallets": [], "boxes": [], "other": [], "collections": {}}

        # First pass: find individual objects
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.visible_get():
                name_lower = obj.name.lower()
                if "pallet" in name_lower:
                    objects["pallets"].append(obj)
                elif "box" in name_lower or "create" in name_lower:
                    objects["boxes"].append(obj)
                else:
                    objects["other"].append(obj)

        # Second pass: find collection-based groups (object.XXX pattern)
        collection_groups = {}

        for obj in bpy.data.objects:
            if obj.type == "MESH":
                # Look for collection-based naming patterns
                parts = obj.name.split(".")
                if len(parts) >= 2:
                    base_name = parts[0].lower()
                    group_id = ".".join(parts[1:])  # Could be "001" or more complex

                    # Initialize collection group if not exists
                    if group_id not in collection_groups:
                        collection_groups[group_id] = {
                            "pallets": [],
                            "boxes": [],
                            "other": [],
                            "group_id": group_id,
                        }

                    # Categorize by base name
                    if "pallet" in base_name:
                        collection_groups[group_id]["pallets"].append(obj)
                        print(
                            f"📦 Found collection pallet: {obj.name} in group {group_id}"
                        )
                    elif "box" in base_name:
                        collection_groups[group_id]["boxes"].append(obj)
                        print(f"📦 Found collection box: {obj.name} in group {group_id}")
                    else:
                        collection_groups[group_id]["other"].append(obj)

        objects["collections"] = collection_groups

        print(
            f"📦 Found: {len(objects['pallets'])} individual pallets, {len(objects['boxes'])} individual boxes"
        )
        print(f"📦 Found: {len(collection_groups)} collection groups")

        for group_id, group in collection_groups.items():
            print(
                f"  Group {group_id}: {len(group['pallets'])} pallets, {len(group['boxes'])} boxes"
            )

        return objects

    def generate_warehouse_path(self, scene_objects):
        """Generate a forklift-like camera path through the warehouse."""
        pallets = scene_objects["pallets"]
        if not pallets:
            # Fallback path
            return [
                {"position": Vector((0, 0, 1.6)), "rotation": Euler((0, 0, 0))},
                {"position": Vector((5, 0, 1.6)), "rotation": Euler((0, 0, 0))},
            ]

        # Calculate warehouse bounds
        all_positions = [p.location for p in pallets]
        min_x = min(pos.x for pos in all_positions) - 5
        max_x = max(pos.x for pos in all_positions) + 5
        min_y = min(pos.y for pos in all_positions) - 5
        max_y = max(pos.y for pos in all_positions) + 5

        # Generate forklift path points
        path = []
        camera_height = self.config.get("camera_height_range", (1.4, 2.0))

        # Create a path that moves through the warehouse
        num_points = max(10, self.config["max_total_images"] // 2)

        for i in range(num_points):
            # Forklift-like movement pattern
            x = min_x + (max_x - min_x) * (i / (num_points - 1))
            y = min_y + (max_y - min_y) * (0.3 + 0.4 * math.sin(i * 0.5))
            z = random.uniform(*camera_height)

            # Add some randomness for realistic movement
            x += random.uniform(-0.5, 0.5)
            y += random.uniform(-0.5, 0.5)

            position = Vector((x, y, z))

            # Look towards nearby pallets
            look_target = self.find_nearest_pallet(position, pallets)
            look_dir = (look_target - position).normalized()
            rotation = look_dir.to_track_quat("-Z", "Y").to_euler()

            path.append({"position": position, "rotation": rotation})

        return path

    def find_nearest_pallet(self, position, pallets):
        """Find the nearest pallet to look at."""
        if not pallets:
            return Vector((0, 0, 0))

        nearest_dist = float("inf")
        nearest_pallet = pallets[0]

        for pallet in pallets:
            dist = (pallet.location - position).length
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_pallet = pallet

        return Vector(nearest_pallet.location)

    def position_camera_on_path(self, cam_obj, camera_path, progress):
        """Position camera along the forklift path with realistic movement."""
        if not camera_path:
            return

        # Interpolate along path
        path_index = progress * (len(camera_path) - 1)
        index_low = int(path_index)
        index_high = min(index_low + 1, len(camera_path) - 1)
        lerp_factor = path_index - index_low

        if index_low == index_high:
            point = camera_path[index_low]
        else:
            point_low = camera_path[index_low]
            point_high = camera_path[index_high]

            # Interpolate position and rotation
            position = point_low["position"].lerp(point_high["position"], lerp_factor)

            # Add forklift-like jitter
            lateral_jitter = self.config.get("camera_lateral_jitter_m", 0.15)
            yaw_jitter = self.config.get("camera_yaw_jitter_deg", 3.0)
            pitch_range = self.config.get("camera_pitch_deg_range", (-3.0, 8.0))

            position.x += random.uniform(-lateral_jitter, lateral_jitter)
            position.y += random.uniform(-lateral_jitter, lateral_jitter)

            rotation = point_low["rotation"].copy()
            rotation.z += math.radians(random.uniform(-yaw_jitter, yaw_jitter))
            rotation.x += math.radians(random.uniform(*pitch_range))

            point = {"position": position, "rotation": rotation}

        # Apply to camera
        cam_obj.location = point["position"]
        cam_obj.rotation_euler = point["rotation"]

    def randomize_scene_objects(self, scene_objects):
        """Randomize scene objects and replace hidden boxes with generated groups - collection-aware approach."""
        removed_objects = []
        modified_objects = []
        original_positions = {}

        print("=== DÉBUT RANDOMISATION COLLECTION-AWARE ===")

        # Find box templates (box1, box2, box3)
        box_templates = []
        print("🔍 Searching for box templates...")
        for obj in bpy.data.objects:
            if obj.type == "MESH" and obj.name in ["box1", "box2", "box3"]:
                box_templates.append(obj)
                print(
                    f"✅ Template found: {obj.name} at {obj.location} (visible: {obj.visible_get()})"
                )

        print(f"Total templates box found: {len(box_templates)}")
        if not box_templates:
            print("⚠️  WARNING: No box1, box2, box3 templates found in scene!")
            print("Available mesh objects:")
            for obj in bpy.data.objects:
                if obj.type == "MESH":
                    print(f"  - {obj.name}")
            # Use existing boxes as templates if no box1,box2,box3 found
            print("Using existing boxes as templates...")
            for box in scene_objects["boxes"][:3]:  # Use first 3 boxes as templates
                box_templates.append(box)
                print(f"✅ Using as template: {box.name}")

        if not box_templates:
            print("❌ CRITICAL: No box templates available at all!")
            return removed_objects, modified_objects, original_positions

        # Clean up previously generated boxes
        self.cleanup_generated_boxes()

        # Create 5 different box groups (from original)
        group_configs = self._create_5_different_box_groups(box_templates)

        # Process collection groups - replace hidden boxes with generated groups
        box_removal_prob = self.config.get("box_removal_probability", 0.7)
        templates_to_keep = {"box1", "box2", "box3"}

        replacement_count = 0

        for group_id, collection_group in scene_objects["collections"].items():
            print(f"\n🎯 Processing collection group: {group_id}")

            # Process boxes in this collection
            for box in collection_group["boxes"]:
                if (
                    box.name.lower() not in templates_to_keep
                    and random.random() < box_removal_prob
                ):
                    print(f"  📦 Hiding box: {box.name}")
                    removed_objects.append(box)
                    original_positions[box] = box.matrix_world.copy()
                    box.hide_viewport = True
                    box.hide_render = True

                    # Find corresponding pallet in same collection
                    corresponding_pallet = None
                    for pallet in collection_group["pallets"]:
                        # Simple matching - could be made more sophisticated
                        corresponding_pallet = pallet
                        break

                    if corresponding_pallet:
                        print(
                            f"  🎯 Found corresponding pallet: {corresponding_pallet.name}"
                        )

                        # Choose random group configuration
                        group_config = random.choice(group_configs)

                        # Generate replacement group using box's original position/scale as reference
                        try:
                            replacement_boxes = self._generate_replacement_box_group(
                                box,
                                corresponding_pallet,
                                group_config,
                                box_templates,
                                group_id,
                            )
                            if replacement_boxes:
                                replacement_count += 1
                            else:
                                print(
                                    f"  ⚠️  Failed to generate replacement for {box.name}"
                                )
                        except Exception as e:
                            print(
                                f"  ❌ Error generating replacement for {box.name}: {e}"
                            )
                            import traceback

                            traceback.print_exc()
                    else:
                        print(f"  ⚠️  No corresponding pallet found for {box.name}")

        # Also process individual boxes (not in collections)
        for box in scene_objects["boxes"]:
            if (
                box.name.lower() not in templates_to_keep
                and random.random() < box_removal_prob
            ):
                print(f"📦 Hiding individual box: {box.name}")
                removed_objects.append(box)
                original_positions[box] = box.matrix_world.copy()
                box.hide_viewport = True
                box.hide_render = True

                # Find nearest pallet for individual boxes
                nearest_pallet = self._find_nearest_pallet_to_box(
                    box, scene_objects["pallets"]
                )
                if nearest_pallet:
                    group_config = random.choice(group_configs)
                    try:
                        replacement_boxes = self._generate_replacement_box_group(
                            box,
                            nearest_pallet,
                            group_config,
                            box_templates,
                            "individual",
                        )
                        if replacement_boxes:
                            replacement_count += 1
                    except Exception as e:
                        print(
                            f"❌ Error generating individual replacement for {box.name}: {e}"
                        )

        print(f"\n🎉 Randomization complete: {replacement_count} box groups generated")
        return removed_objects, modified_objects, original_positions

    def _is_box_on_pallet(self, box, pallet):
        """Check if a box is positioned on top of a pallet."""
        # Simple distance check - box should be close to pallet XY and above it
        pallet_loc = pallet.location
        box_loc = box.location

        # Check if box is roughly above the pallet (within 2m XY distance and above in Z)
        xy_distance = (
            (box_loc.x - pallet_loc.x) ** 2 + (box_loc.y - pallet_loc.y) ** 2
        ) ** 0.5
        z_above = box_loc.z > pallet_loc.z

        return xy_distance < 2.0 and z_above

    def _create_5_different_box_groups(self, box_templates):
        """Create 5 different box group configurations - from original warehouse generator."""
        print(f"🔧 Creating group configurations with {len(box_templates)} templates")

        if not box_templates:
            print("❌ No box templates available for groups!")
            return []

        # Configuration from original - 5 different group patterns
        group_configs = [
            {
                "rows": 1,
                "cols": 2,
                "count": 2,
                "stack_layers": (1, 2),
                "stack_prob": 0.3,
                "id": 0,
            },
            {
                "rows": 2,
                "cols": 2,
                "count": 3,
                "stack_layers": (2, 3),
                "stack_prob": 0.6,
                "id": 1,
            },
            {
                "rows": 1,
                "cols": 3,
                "count": 3,
                "stack_layers": (1, 2),
                "stack_prob": 0.4,
                "id": 2,
            },
            {
                "rows": 2,
                "cols": 3,
                "count": 4,
                "stack_layers": (2, 4),
                "stack_prob": 0.7,
                "id": 3,
            },
            {
                "rows": 1,
                "cols": 1,
                "count": 1,
                "stack_layers": (3, 5),
                "stack_prob": 0.9,
                "id": 4,
            },
        ]

        for config in group_configs:
            config["box_templates"] = box_templates.copy()

        print(f"✅ {len(group_configs)} group configurations created")
        return group_configs

    def _find_nearest_pallet_to_box(self, box, pallets):
        """Find the nearest pallet to a given box."""
        if not pallets:
            return None

        min_distance = float("inf")
        nearest_pallet = None

        for pallet in pallets:
            distance = (box.location - pallet.location).length
            if distance < min_distance:
                min_distance = distance
                nearest_pallet = pallet

        return nearest_pallet

    def _generate_replacement_box_group(
        self, original_box, target_pallet, group_config, box_templates, group_id
    ):
        """Generate replacement box group using EXACT original _place_box_group_on_pallet method."""
        print(
            f"    🎯 Generating replacement group (config {group_config['id']}) for {original_box.name}"
        )

        # Use EXACT original method with modified collection placement
        return self._place_box_group_on_pallet_exact(
            group_config, target_pallet, box_templates, group_id
        )

    def _place_box_group_on_pallet_exact(
        self, group_data, pallet, box_templates, group_id
    ):
        """EXACT copy of original _place_box_group_on_pallet but with collection-aware naming and anti-collapse measures."""

        if not box_templates or not pallet:
            print("❌ Templates ou palette manquants!")
            return []

        try:
            boxes_collection = self._create_boxes_collection_for_pallet_exact(
                pallet, group_id
            )

            # Measures palette - EXACT from original with validation
            bpy.context.view_layer.update()
            try:
                world_corners = [
                    pallet.matrix_world @ Vector(c) for c in pallet.bound_box
                ]
                pallet_top_z = max(c.z for c in world_corners)

                # bornes locales (pour grille)
                pxs = [v[0] for v in pallet.bound_box]
                pys = [v[1] for v in pallet.bound_box]
                pzs = [v[2] for v in pallet.bound_box]
                pl_min_x, pl_max_x = min(pxs), max(pxs)
                pl_min_y, pl_max_y = min(pys), max(pys)
                pl_top_z = max(pzs)

                # Validate bounds to prevent degenerate dimensions
                if abs(pl_max_x - pl_min_x) < 0.1:
                    print(
                        f"⚠️ Pallet width too small: {abs(pl_max_x - pl_min_x):.3f}, using fallback"
                    )
                    pl_min_x, pl_max_x = -0.6, 0.6
                if abs(pl_max_y - pl_min_y) < 0.1:
                    print(
                        f"⚠️ Pallet depth too small: {abs(pl_max_y - pl_min_y):.3f}, using fallback"
                    )
                    pl_min_y, pl_max_y = -0.4, 0.4

            except Exception:
                pallet_top_z = pallet.location.z + getattr(pallet.dimensions, "z", 0.15)
                w = max(0.5, getattr(pallet.dimensions, "x", 1.2))
                d = max(0.5, getattr(pallet.dimensions, "y", 0.8))
                pl_min_x, pl_max_x = -w / 2, w / 2
                pl_min_y, pl_max_y = -d / 2, d / 2
                pl_top_z = 0.0

            # Choix grille: 2 (1x2 ou 2x1 selon axe long) ou 4 (2x2) - EXACT from original
            top_w_local = pl_max_x - pl_min_x
            top_d_local = pl_max_y - pl_min_y

            print(f"  Pallet dimensions: {top_w_local:.3f} x {top_d_local:.3f} (local)")

            if random.random() < 0.5:
                if abs(top_w_local) >= abs(top_d_local):
                    grid_x, grid_y = 2, 1
                else:
                    grid_x, grid_y = 1, 2
            else:
                grid_x, grid_y = 2, 2

            cell_width_local = (pl_max_x - pl_min_x) / grid_x
            cell_depth_local = (pl_max_y - pl_min_y) / grid_y

            print(
                f"  Grid: {grid_x}x{grid_y}, cell size: {cell_width_local:.3f} x {cell_depth_local:.3f}"
            )

            created_objects = []
            obj_index = 0
            placed_positions = []  # Track positions to prevent overlap

            for row in range(grid_y):
                for col in range(grid_x):
                    # Centre de cellule en local -> monde - EXACT from original
                    local_cx = pl_min_x + (col + 0.5) * cell_width_local
                    local_cy = pl_min_y + (row + 0.5) * cell_depth_local
                    local_pos = Vector((local_cx, local_cy, pl_top_z))
                    world_pos = pallet.matrix_world @ local_pos

                    print(
                        f"      Cell [{row},{col}]: local({local_cx:.2f}, {local_cy:.2f}, {pl_top_z:.2f}) → world({world_pos.x:.2f}, {world_pos.y:.2f}, {world_pos.z:.2f})"
                    )

                    template = random.choice(box_templates)
                    box = template.copy()
                    box.data = template.data.copy()
                    box.name = f"{self.attached_group_prefix}G{group_data['id']}_{obj_index}_L0_{template.name}_{group_id}"
                    self._add_box_to_collection_exact(box, boxes_collection)

                    # SAFE ORDER: Position first (world space)
                    safe_z = max(
                        pallet_top_z + 0.05, world_pos.z + 0.05
                    )  # Ensure above pallet
                    initial_pos = Vector((world_pos.x, world_pos.y, safe_z))
                    box.location = initial_pos

                    # Check for overlap with existing boxes
                    min_distance = 0.1  # Minimum distance between box centers
                    for prev_pos in placed_positions:
                        distance = (
                            Vector((initial_pos.x, initial_pos.y))
                            - Vector((prev_pos.x, prev_pos.y))
                        ).length
                        if distance < min_distance:
                            # Adjust position to avoid overlap
                            offset = Vector((0.1 * col, 0.1 * row))
                            initial_pos += offset
                            box.location = initial_pos
                            print(
                                f"      ⚠️ Overlap detected, adjusted position by {offset}"
                            )
                            break

                    placed_positions.append(initial_pos)
                    print(f"      Initial position: {box.location}")

                    # Orientation + scale par axe pour remplir la cellule - EXACT from original with safety
                    try:
                        dim_x = max(
                            0.01, getattr(template.dimensions, "x", 0.1)
                        )  # Prevent zero dimensions
                        dim_y = max(0.01, getattr(template.dimensions, "y", 0.1))

                        # 0° vs 90° (choix qui fitte le mieux)
                        sx0 = abs(cell_width_local) / dim_x
                        sy0 = abs(cell_depth_local) / dim_y
                        sx90 = abs(cell_width_local) / dim_y
                        sy90 = abs(cell_depth_local) / dim_x

                        use_90 = (sx90 * sy90) > (sx0 * sy0)
                        if use_90:
                            yaw = pallet.rotation_euler.z + math.pi / 2
                            scale_x, scale_y = sx90, sy90
                        else:
                            yaw = pallet.rotation_euler.z
                            scale_x, scale_y = sx0, sy0

                        # CONSERVATIVE scaling to prevent collapse - much tighter limits
                        scale_x = max(0.2, min(3.0, scale_x))  # More conservative range
                        scale_y = max(0.2, min(3.0, scale_y))

                        # Additional check: if scaling is too extreme, use moderate values
                        if scale_x > 2.5 or scale_y > 2.5:
                            scale_x = min(2.0, scale_x)
                            scale_y = min(2.0, scale_y)
                            print("      📏 Applied conservative scaling limit")

                        print(
                            f"      Scaling: template_dim({dim_x:.2f}, {dim_y:.2f}) → scale({scale_x:.2f}, {scale_y:.2f}) {'90°' if use_90 else '0°'}"
                        )

                    except Exception as e:
                        print(f"      ⚠️ Scaling error: {e}")
                        yaw = pallet.rotation_euler.z
                        scale_x = scale_y = 1.0

                    # SAFE ORDER: Apply scale and rotation
                    box.scale = Vector((scale_x, scale_y, 1.0))
                    box.rotation_euler = Euler((0, 0, yaw))

                    # Update transforms to ensure proper dimensions calculation
                    bpy.context.view_layer.update()

                    # SAFE ORDER: Align bottom to pallet top with generous margin
                    try:
                        self._align_bottom_to_z(box, pallet_top_z, margin=0.03)
                    except Exception as e:
                        print(
                            f"      ⚠️ Alignment error: {e}, using manual positioning"
                        )
                        # Manual fallback positioning
                        box.location.z = pallet_top_z + 0.05

                    # Update transforms again before parenting
                    bpy.context.view_layer.update()

                    # SAFE ORDER: Parent while preserving world position
                    try:
                        self._parent_preserve_world(box, pallet)
                    except Exception as e:
                        print(f"      ⚠️ Parenting error: {e}")
                        # Manual parenting fallback
                        box.parent = pallet

                    # Final update and visibility
                    bpy.context.view_layer.update()
                    box.hide_viewport = False
                    box.hide_render = False

                    created_objects.append(box)
                    obj_index += 1

            # Final scene update
            bpy.context.view_layer.update()
            print(
                f"  🎯 Created {len(created_objects)} boxes with anti-collapse measures"
            )
            return created_objects

        except Exception as e:
            print(f"❌ Erreur placement (exact method): {e}")
            import traceback

            traceback.print_exc()
            return []

    def _create_boxes_collection_for_pallet_exact(self, pallet, group_id):
        """Create collection for pallet boxes - adapted for collection-aware structure."""
        collection_name = f"boxes_group_{pallet.name}_{group_id}"

        # Check if collection exists
        if collection_name in bpy.data.collections:
            boxes_collection = bpy.data.collections[collection_name]
            # Clear existing objects
            for obj in list(boxes_collection.objects):
                try:
                    boxes_collection.objects.unlink(obj)
                    if obj.name.startswith(self.attached_group_prefix):
                        bpy.data.objects.remove(obj, do_unlink=True)
                except Exception:
                    pass
        else:
            # Create new collection
            boxes_collection = bpy.data.collections.new(collection_name)

        # Find the collection that contains this pallet (object.XXX structure)
        pallet_parent_collection = None

        # Look for collection containing this pallet
        for collection in bpy.data.collections:
            try:
                if pallet.name in [obj.name for obj in collection.objects]:
                    # Found collection containing the pallet
                    pallet_parent_collection = collection
                    break
            except Exception:
                continue

        # If no specific collection found, use scene collection
        if pallet_parent_collection is None:
            pallet_parent_collection = bpy.context.scene.collection

        # Link the boxes collection to the same parent collection as the pallet
        if boxes_collection.name not in pallet_parent_collection.children:
            pallet_parent_collection.children.link(boxes_collection)

        return boxes_collection

    def _add_box_to_collection_exact(self, box, boxes_collection):
        """Add box to collection - EXACT from original."""
        if not box or not boxes_collection:
            print("❌ Boîte ou collection invalid!")
            return

        try:
            # Remove from all other collections
            for collection in list(box.users_collection):
                with contextlib.suppress(Exception):
                    collection.objects.unlink(box)

            # Add to boxes collection
            boxes_collection.objects.link(box)

        except Exception as e:
            print(f"❌ Erreur ajout à collection: {e}")

    def generate_pallet_box_group(self, pallet, box_templates):
        """Generate a group of boxes on a pallet - EXACT logic from original warehouse generator."""
        if not box_templates:
            print(f"❌ Templates ou palette manquants pour {pallet.name}!")
            return []

        print(
            f"Génération de box sur {pallet.name} avec {len(box_templates)} templates"
        )

        try:
            # Create collection for this pallet's boxes
            boxes_collection = self._create_boxes_collection_for_pallet(pallet)

            # Get pallet measurements in world and local space
            bpy.context.view_layer.update()

            try:
                world_corners = [
                    pallet.matrix_world @ Vector(c) for c in pallet.bound_box
                ]
                pallet_top_z = max(c.z for c in world_corners)

                # Local bounds for grid calculation
                pxs = [v[0] for v in pallet.bound_box]
                pys = [v[1] for v in pallet.bound_box]
                pzs = [v[2] for v in pallet.bound_box]
                pl_min_x, pl_max_x = min(pxs), max(pxs)
                pl_min_y, pl_max_y = min(pys), max(pys)
                pl_top_z = max(pzs)
            except Exception:
                # Fallback if bound_box fails
                pallet_top_z = pallet.location.z + getattr(pallet.dimensions, "z", 0.15)
                w = max(0.5, getattr(pallet.dimensions, "x", 1.2))
                d = max(0.5, getattr(pallet.dimensions, "y", 0.8))
                pl_min_x, pl_max_x = -w / 2, w / 2
                pl_min_y, pl_max_y = -d / 2, d / 2
                pl_top_z = 0.0

            # Choose grid: 2 boxes (1x2 or 2x1) or 4 boxes (2x2) - EXACT original logic
            top_w_local = pl_max_x - pl_min_x
            top_d_local = pl_max_y - pl_min_y

            if random.random() < 0.5:
                # 2 boxes
                if abs(top_w_local) >= abs(top_d_local):
                    grid_x, grid_y = 2, 1
                else:
                    grid_x, grid_y = 1, 2
            else:
                # 4 boxes
                grid_x, grid_y = 2, 2

            cell_width_local = (pl_max_x - pl_min_x) / grid_x
            cell_depth_local = (pl_max_y - pl_min_y) / grid_y

            print(f"  Grille: {grid_y}x{grid_x} sur palette {pallet.name}")

            created_objects = []
            obj_index = 0

            # Place boxes in grid - EXACT original logic
            for row in range(grid_y):
                for col in range(grid_x):
                    # Cell center in local coordinates -> world coordinates
                    local_cx = pl_min_x + (col + 0.5) * cell_width_local
                    local_cy = pl_min_y + (row + 0.5) * cell_depth_local
                    local_pos = Vector((local_cx, local_cy, pl_top_z))
                    world_pos = pallet.matrix_world @ local_pos

                    # Create box from template
                    template = random.choice(box_templates)
                    box = template.copy()
                    box.data = template.data.copy()
                    box.name = (
                        f"{self.attached_group_prefix}G0_{obj_index}_L0_{template.name}"
                    )

                    # CRITICAL: Ensure template is visible for copying
                    if template.hide_viewport:
                        print(
                            f"⚠️  Template {template.name} is hidden in viewport - making visible for copying"
                        )
                        template.hide_viewport = False
                    if template.hide_render:
                        print(
                            f"⚠️  Template {template.name} is hidden in render - making visible for copying"
                        )
                        template.hide_render = False

                    # Add to collection FIRST
                    self._add_box_to_collection(box, boxes_collection)

                    # Position in world coordinates - EXACT original logic
                    box.location = world_pos
                    print(
                        f"    Box {obj_index}: template={template.name}, local({local_cx:.2f},{local_cy:.2f},{pl_top_z:.2f}) -> world({world_pos.x:.2f},{world_pos.y:.2f},{world_pos.z:.2f})"
                    )
                    print(f"    Box {obj_index}: final location = {box.location}")

                    # Scale to fill cell exactly - EXACT original logic
                    try:
                        dim_x = max(1e-4, template.dimensions.x)
                        dim_y = max(1e-4, template.dimensions.y)

                        # Test 0° vs 90° rotation (choose best fit)
                        sx0 = abs(cell_width_local) / dim_x
                        sy0 = abs(cell_depth_local) / dim_y
                        sx90 = abs(cell_width_local) / dim_y
                        sy90 = abs(cell_depth_local) / dim_x

                        use_90 = (sx90 * sy90) > (sx0 * sy0)
                        if use_90:
                            yaw = pallet.rotation_euler.z + math.pi / 2
                            scale_x, scale_y = sx90, sy90
                        else:
                            yaw = pallet.rotation_euler.z
                            scale_x, scale_y = sx0, sy0
                    except Exception:
                        yaw = pallet.rotation_euler.z
                        scale_x = scale_y = 1.0

                    # Apply scaling (preserve Z scale)
                    box.scale = Vector((scale_x, scale_y, 1.0))
                    box.rotation_euler = Euler((0, 0, yaw))

                    # Align bottom to pallet top using world coordinates - EXACT original logic
                    self._align_bottom_to_z(box, pallet_top_z, margin=0.0)

                    # CRITICAL: Parent to pallet while preserving world position - EXACT from original
                    self._parent_preserve_world(box, pallet)

                    # CRITICAL: Ensure visibility
                    box.hide_viewport = False
                    box.hide_render = False
                    box.hide_select = False

                    # Force update
                    bpy.context.view_layer.update()

                    created_objects.append(box)
                    obj_index += 1

            bpy.context.view_layer.update()
            print(f"✅ {len(created_objects)} box générées sur {pallet.name}")

            # Debug: verify boxes are in scene
            for box in created_objects:
                in_scene = box.name in bpy.data.objects
                visible = not box.hide_viewport and not box.hide_render
                print(
                    f"    Debug box {box.name}: in_scene={in_scene}, visible={visible}, location={box.location}"
                )

            return created_objects

        except Exception as e:
            print(f"❌ Erreur placement sur {pallet.name}: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _create_boxes_collection_for_pallet(self, pallet):
        """Create collection for pallet boxes - EXACT from original."""
        collection_name = f"boxes_group_{pallet.name}"

        # Check if collection exists
        if collection_name in bpy.data.collections:
            boxes_collection = bpy.data.collections[collection_name]
            # Clear existing objects
            for obj in list(boxes_collection.objects):
                with contextlib.suppress(Exception):
                    boxes_collection.objects.unlink(obj)
        else:
            # Create new collection
            boxes_collection = bpy.data.collections.new(collection_name)

        # Find pallet's parent collection
        pallet_parent_collection = None

        # Check scene collection first
        if pallet.name in bpy.context.scene.collection.objects:
            pallet_parent_collection = bpy.context.scene.collection
        else:
            # Search in all collections
            for collection in bpy.data.collections:
                with contextlib.suppress(Exception):
                    if pallet.name in collection.objects:
                        pallet_parent_collection = collection
                        break

        # Use scene collection as fallback
        if pallet_parent_collection is None:
            pallet_parent_collection = bpy.context.scene.collection

        # Link collection at same level as pallet
        if boxes_collection.name not in pallet_parent_collection.children:
            pallet_parent_collection.children.link(boxes_collection)

        return boxes_collection

    def _add_box_to_collection(self, box, boxes_collection):
        """Add box to collection - EXACT from original."""
        if not box or not boxes_collection:
            print("❌ Boîte ou collection invalid!")
            return

        try:
            # Remove from all other collections
            for collection in list(box.users_collection):
                with contextlib.suppress(Exception):
                    collection.objects.unlink(box)

            # Add to boxes collection
            boxes_collection.objects.link(box)

        except Exception as e:
            print(f"❌ Erreur ajout à collection: {e}")

    def _align_bottom_to_z(self, obj, target_z, margin=0.0):
        """Align object bottom to target Z coordinate - EXACT from original with improved robustness."""
        try:
            bpy.context.view_layer.update()

            # Get the actual bottom of the object in world space
            bottom = self._get_object_bottom_z(obj)

            # Calculate the offset needed
            dz = (target_z + margin) - bottom

            # Only adjust if there's a significant difference (avoid micro-adjustments)
            if abs(dz) > 1e-4:
                old_z = obj.location.z
                obj.location.z += dz
                print(
                    f"        Aligned {obj.name}: Z {old_z:.3f} → {obj.location.z:.3f} (offset: {dz:.3f})"
                )
                bpy.context.view_layer.update()

        except Exception as e:
            print(f"⚠️ Erreur align_bottom_to_z for {obj.name}: {e}")
            # Fallback: simple positioning
            obj.location.z = target_z + margin

    def _get_object_bottom_z(self, obj):
        """Return the bottom Z coordinate of an object in world space - EXACT from original with better error handling."""
        try:
            bpy.context.view_layer.update()

            # Transform all bounding box corners to world space
            corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            bottom_z = min(c.z for c in corners)

            return bottom_z

        except Exception as e:
            print(f"⚠️ Error getting bottom Z for {obj.name}: {e}")
            try:
                # Fallback calculation
                return obj.location.z - (obj.dimensions.z * max(obj.scale)) * 0.5
            except Exception:
                return obj.location.z

    def _parent_preserve_world(self, child_obj, parent_obj):
        """Parent child to parent while preserving world transform - EXACT from original with better error handling."""
        if not child_obj or not parent_obj:
            return

        try:
            # Save current world transform
            mat_w = child_obj.matrix_world.copy()

            # Set parent
            child_obj.parent = parent_obj

            # Calculate and set parent inverse matrix to preserve world position
            child_obj.matrix_parent_inverse = parent_obj.matrix_world.inverted() @ mat_w

            # Ensure world transform is preserved
            child_obj.matrix_world = mat_w

            print(
                f"        Parented {child_obj.name} to {parent_obj.name}, world pos preserved: {child_obj.location}"
            )

        except Exception as e:
            print(f"⚠️ Error in parent_preserve_world for {child_obj.name}: {e}")
            # Fallback: simple parenting
            with contextlib.suppress(Exception):
                child_obj.parent = parent_obj

    def cleanup_generated_boxes(self):
        """Clean up previously generated boxes."""
        to_remove = [
            obj
            for obj in bpy.data.objects
            if obj.name.startswith(self.attached_group_prefix)
        ]
        for obj in to_remove:
            with contextlib.suppress(Exception):
                bpy.data.objects.remove(obj, do_unlink=True)

    def find_pallet_box_relationships(self, scene_objects):
        """Find relationships between pallets and their boxes."""
        relationships = []
        for pallet in scene_objects["pallets"]:
            boxes = [
                obj
                for obj in bpy.data.objects
                if obj.name.startswith(f"{self.attached_group_prefix}{pallet.name}_")
            ]
            relationships.append({"pallet": pallet, "boxes": boxes})
        return relationships

    def get_visible_pallets(self, scene_objects, cam_obj, sc):
        """Get pallets that are visible in the current camera view."""
        visible_pallets = []

        for pallet in scene_objects["pallets"]:
            bbox_2d = self.get_bbox_2d_accurate(pallet, cam_obj, sc)
            if bbox_2d and bbox_2d["area"] > self.config.get("min_pallet_area", 100):
                pallet_info = {
                    "pallet": pallet,
                    "bbox_2d": bbox_2d,
                    "bbox_3d": self.bbox_3d_oriented(pallet),
                    "generated_boxes": [
                        obj
                        for obj in bpy.data.objects
                        if obj.name.startswith(
                            f"{self.attached_group_prefix}{pallet.name}_"
                        )
                    ],
                }
                visible_pallets.append(pallet_info)

        return visible_pallets

    def randomize_lighting(self):
        """Set up dynamic warehouse lighting."""
        # Remove existing synthetic lights
        for obj in [
            o
            for o in bpy.data.objects
            if o.type == "LIGHT" and o.name.startswith("SynthLight_")
        ]:
            bpy.data.objects.remove(obj, do_unlink=True)

        # Create warehouse-appropriate lighting
        light_count = random.randint(*self.config.get("light_count_range", (2, 4)))
        energy_ranges = self.config.get("light_energy_ranges", {})

        for i in range(light_count):
            light_type = random.choice(["AREA", "SPOT", "POINT"])
            light_data = bpy.data.lights.new(
                f"SynthLightData_{light_type}_{i}", light_type
            )
            light_obj = bpy.data.objects.new(f"SynthLight_{light_type}_{i}", light_data)
            bpy.context.collection.objects.link(light_obj)

            # Set light properties
            energy_range = energy_ranges.get(light_type, (100, 500))
            light_data.energy = random.uniform(*energy_range)

            if light_type == "AREA":
                light_data.size = random.uniform(2.0, 5.0)
            elif light_type == "SPOT":
                light_data.spot_size = math.radians(random.uniform(30, 60))

            # Position light (warehouse ceiling height)
            light_obj.location = Vector(
                (
                    random.uniform(-10, 10),
                    random.uniform(-10, 10),
                    random.uniform(8, 15),
                )
            )

            # Point downward
            light_obj.rotation_euler = Euler((math.radians(180), 0, 0))

            # Optional colored lighting
            if self.config.get(
                "use_colored_lights", True
            ) and random.random() < self.config.get("colored_light_probability", 0.3):
                light_data.color = (
                    random.uniform(0.8, 1.0),
                    random.uniform(0.8, 1.0),
                    random.uniform(0.9, 1.0),
                )

    def save_warehouse_frame_outputs(
        self,
        frame_id,
        img_filename,
        img_path,
        visible_pallets,
        cam_obj,
        sc,
        coco_data,
        meta,
    ):
        """Save all outputs for a warehouse frame."""
        img_w, img_h = self.config["resolution_x"], self.config["resolution_y"]

        # COCO image entry
        coco_image = {
            "id": frame_id,
            "file_name": img_filename,
            "width": img_w,
            "height": img_h,
        }
        coco_data["images"].append(coco_image)

        # Write annotations
        self.write_warehouse_annotations(
            visible_pallets, coco_data, frame_id, img_w, img_h, cam_obj, sc
        )

        # Generate analysis image using comprehensive analysis from base class
        if self.config.get("generate_analysis", True):  # Default to True
            try:
                # Convert visible_pallets format to match what create_analysis_image_multi expects
                b2d_list = [p["bbox_2d"] for p in visible_pallets]
                b3d_list = [p["bbox_3d"] for p in visible_pallets]
                pockets_list = [p.get("hole_bboxes", []) for p in visible_pallets]

                ana_path = os.path.join(
                    self.paths["analysis"], f"analysis_{img_filename}"
                )
                success = self.create_analysis_image_multi(
                    img_path,
                    b2d_list,
                    b3d_list,
                    pockets_list,
                    cam_obj,
                    sc,
                    ana_path,
                    frame_id,
                )
                if success:
                    print(f"📊 Warehouse analysis image saved: {ana_path}")
                else:
                    print(f"⚠️ Failed to create analysis image for frame {frame_id}")
            except Exception as e:
                print(f"    ⚠️ Analysis generation error: {e}")

        # Metadata
        meta.append(
            {
                "frame": frame_id,
                "image_id": img_filename[:-4],  # Remove .png
                "rgb": img_path,
                "visible_pallets": len(visible_pallets),
                "camera": {
                    "position": list(cam_obj.location),
                    "rotation": list(cam_obj.rotation_euler),
                },
            }
        )

    def write_warehouse_annotations(
        self, visible_pallets, coco_data, img_id, img_w, img_h, cam_obj, sc
    ):
        """Write COCO and YOLO annotations for warehouse scene."""
        yolo_lines = []

        for pallet_info in visible_pallets:
            # Pallet annotation
            bbox = pallet_info["bbox_2d"]
            annotation = {
                "id": len(coco_data["annotations"]) + 1,
                "image_id": img_id,
                "category_id": 1,  # Pallet
                "bbox": [bbox["x_min"], bbox["y_min"], bbox["width"], bbox["height"]],
                "area": bbox["area"],
                "iscrowd": 0,
                "segmentation": [],
            }
            coco_data["annotations"].append(annotation)

            # YOLO format
            x_center = (bbox["x_min"] + bbox["x_max"]) / 2 / img_w
            y_center = (bbox["y_min"] + bbox["y_max"]) / 2 / img_h
            width = bbox["width"] / img_w
            height = bbox["height"] / img_h
            yolo_lines.append(
                f"0 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
            )

            # Generated boxes on pallet
            for box in pallet_info.get("generated_boxes", []):
                box_bbox = self.get_bbox_2d_accurate(box, cam_obj, sc)
                if box_bbox and box_bbox["area"] > 50:
                    box_annotation = {
                        "id": len(coco_data["annotations"]) + 1,
                        "image_id": img_id,
                        "category_id": 3,  # Box
                        "bbox": [
                            box_bbox["x_min"],
                            box_bbox["y_min"],
                            box_bbox["width"],
                            box_bbox["height"],
                        ],
                        "area": box_bbox["area"],
                        "iscrowd": 0,
                        "segmentation": [],
                    }
                    coco_data["annotations"].append(box_annotation)

                    # YOLO format for box
                    x_center = (box_bbox["x_min"] + box_bbox["x_max"]) / 2 / img_w
                    y_center = (box_bbox["y_min"] + box_bbox["y_max"]) / 2 / img_h
                    width = box_bbox["width"] / img_w
                    height = box_bbox["height"] / img_h
                    yolo_lines.append(
                        f"2 {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"
                    )

        # Write YOLO file
        yolo_file = os.path.join(self.paths["yolo"], f"{img_id:06d}.txt")
        with open(yolo_file, "w") as f:
            f.write("\n".join(yolo_lines))

    def restore_scene_objects(self, removed_objects, original_positions):
        """Restore scene objects to original state."""
        for obj in removed_objects:
            obj.hide_viewport = False
            obj.hide_render = False

        # Restore original positions
        for obj, matrix in original_positions.items():
            if obj and hasattr(obj, "matrix_world"):
                obj.matrix_world = matrix

    def save_generated_scene(self, scene_id):
        """
        Save the current generated scene to a .blend file in the scenes folder.
        This allows inspection and reuse of the randomized warehouse layout.
        """
        import os
        from pathlib import Path

        # Create scenes folder if it doesn't exist
        scenes_folder = Path("scenes")
        scenes_folder.mkdir(exist_ok=True)

        # Generate scene filename with batch info
        batch_name = os.path.basename(self.config.get("output_dir", "unknown_batch"))

        # Create a subfolder inside scenes for better organization
        scenes_warehouse_folder = scenes_folder / "warehouse_generated"
        scenes_warehouse_folder.mkdir(exist_ok=True)

        scene_filename = f"warehouse_generated_scene_{scene_id+1}_{batch_name}.blend"
        scene_path = scenes_warehouse_folder / scene_filename

        try:
            print(f"💾 Saving generated scene to: {scene_path}")
            import sys

            sys.stdout.flush()
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
            print(f"✅ Scene saved successfully: {scene_filename}")
            sys.stdout.flush()

            # Also save scene info as JSON for reference
            scene_info = {
                "scene_id": scene_id + 1,
                "batch_folder": batch_name,
                "config_used": {
                    "num_scenes": self.config.get("num_scenes", "unknown"),
                    "max_images_per_scene": self.config.get(
                        "max_images_per_scene", "unknown"
                    ),
                    "box_removal_probability": self.config.get(
                        "box_removal_probability", "unknown"
                    ),
                    "pallet_groups_to_fill": self.config.get(
                        "pallet_groups_to_fill", "unknown"
                    ),
                },
                "timestamp": str(__import__("datetime").datetime.now()),
            }

            info_path = (
                scenes_warehouse_folder
                / f"warehouse_scene_{scene_id+1}_{batch_name}_info.json"
            )
            with open(info_path, "w") as f:
                import json

                json.dump(scene_info, f, indent=2)

        except Exception as e:
            print(f"⚠️  Failed to save generated scene: {e}")
            import sys

            sys.stdout.flush()
