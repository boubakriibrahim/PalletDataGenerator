"""
Warehouse Mode - Based on original warehouse_generator.py

Implements the exact forklift simulation, camera paths, and generation logic
from the original warehouse generator.
"""

import contextlib
import json
import logging
import math
import os
import random
from pathlib import Path

import bpy
import bpy_extras
import numpy as np
from mathutils import Euler, Vector

from .base_generator import BaseGenerator

# Disable PIL debug messages
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

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

        # Set default warehouse-specific config values
        self.config.setdefault("warehouse_occlusion_detection", True)
        self.config.setdefault(
            "warehouse_max_faces_per_pallet", 2
        )  # Allow more faces per pallet
        self.config.setdefault(
            "warehouse_occlusion_tolerance", 0.1
        )  # Reduced tolerance for better occlusion detection
        self.config.setdefault(
            "warehouse_comprehensive_occlusion", True
        )  # Use comprehensive occlusion (check all objects)
        self.config.setdefault(
            "warehouse_min_object_size", 0.2
        )  # Larger minimum object size to ignore small objects
        self.config.setdefault(
            "warehouse_simplified_legend", True
        )  # Use simplified legend with stats only
        self.config.setdefault(
            "warehouse_debug_occlusion", True
        )  # Enable detailed occlusion debugging
        self.config.setdefault(
            "warehouse_disable_occlusion_for_testing", False
        )  # Temporarily disable occlusion for testing
        self.config.setdefault(
            "visualize_camera_path", True
        )  # Enable camera path visualization
        self.config.setdefault(
            "save_scene_with_path", True
        )  # Save scene with camera path visualization

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

            # Always generate and save path visualization before frame generation
            print(f"📊 Generating path visualization for scene {scene_id + 1}...")
            obstacles = self.get_all_obstacles_with_bounds(
                scene_objects["pallets"],
                scene_objects["boxes"],
                scene_objects["collections"],
            )
            warehouse_bounds = self.calculate_warehouse_bounds(obstacles)
            self.generate_and_save_path_visualization(
                camera_path, obstacles, warehouse_bounds, scene_id
            )

            # Create and save camera path visualization
            path_objects = []
            if self.config.get("visualize_camera_path", True):
                print(
                    f"🎬 Creating camera path visualization for scene {scene_id + 1}..."
                )
                path_objects = self.create_camera_path_visualization(
                    camera_path, scene_id
                )

                # Save scene with path visualization
                if self.config.get("save_scene_with_path", True):
                    self.save_generated_scene_with_path(scene_id, camera_path)

                # Hide path visualization from scene before frame generation
                print("🧹 Hiding camera path visualization from scene...")
                self.hide_camera_path_visualization(path_objects)

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

                # Detect faces and generate keypoints for all visible pallets
                keypoints_data = self.generate_keypoints_for_frame(
                    cam_obj, sc, frame_id
                )

                # Debug output for keypoints
                if keypoints_data:
                    print(
                        f"🎯 Frame {frame_id}: Detected {len(keypoints_data)} faces with keypoints"
                    )
                    for face_data in keypoints_data:
                        visible_kp = sum(
                            1 for kp in face_data["keypoints"] if kp["visible"]
                        )
                        print(
                            f"   - {face_data['face_name']} face: {visible_kp}/6 keypoints visible"
                        )
                else:
                    print(f"🎯 Frame {frame_id}: No faces detected for keypoints")

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
                    keypoints_data,
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

        # Clean up camera path visualization after all generation is complete
        print("🧹 Cleaning up camera path visualization...")
        for collection in bpy.data.collections:
            if "CameraPath_Scene" in collection.name:
                # Get all objects in the path collection before removing it
                path_objects = list(collection.objects)
                self.remove_camera_path_visualization(path_objects)
                break

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
        """Generate a realistic forklift-like camera path through the warehouse that avoids obstacles."""
        pallets = scene_objects["pallets"]
        boxes = scene_objects.get("boxes", [])
        collections = scene_objects.get("collections", {})

        if not pallets:
            # Fallback path
            return [
                {"position": Vector((0, 0, 1.6)), "rotation": Euler((0, 0, 0))},
                {"position": Vector((5, 0, 1.6)), "rotation": Euler((0, 0, 0))},
            ]

        # Get all obstacles with their bounding boxes
        all_obstacles = self.get_all_obstacles_with_bounds(pallets, boxes, collections)

        # Calculate proper warehouse bounds from obstacle bounding boxes
        warehouse_bounds = self.calculate_warehouse_bounds(all_obstacles)

        print(
            f"🏭 Warehouse bounds: X({warehouse_bounds['min_x']:.1f} to {warehouse_bounds['max_x']:.1f}), Y({warehouse_bounds['min_y']:.1f} to {warehouse_bounds['max_y']:.1f})"
        )
        print(f"🚧 Found {len(all_obstacles)} obstacles to avoid")

        # Generate realistic forklift path points
        path = []
        camera_height = self.config.get("camera_height_range", (1.4, 2.0))
        num_points = max(10, self.config["max_total_images"] // 2)

        # Create a path that follows warehouse aisles
        safety_margin = 2.5  # Larger safety distance from obstacles

        # Generate realistic warehouse path between left and right collections
        waypoints = self.generate_realistic_warehouse_path(
            all_obstacles, warehouse_bounds, safety_margin
        )

        if not waypoints:
            # Fallback to simple path if no safe waypoints found
            waypoints = [
                Vector(
                    (
                        warehouse_bounds["min_x"] + 3,
                        warehouse_bounds["min_y"] + 3,
                        camera_height[0],
                    )
                ),
                Vector(
                    (
                        warehouse_bounds["max_x"] - 3,
                        warehouse_bounds["max_y"] - 3,
                        camera_height[0],
                    )
                ),
            ]

        print(f"📍 Generated {len(waypoints)} realistic warehouse waypoints")

        # Create smooth path between waypoints
        for i in range(num_points):
            # Interpolate between waypoints
            t = i / (num_points - 1) if num_points > 1 else 0
            waypoint_index = int(t * (len(waypoints) - 1))
            next_waypoint_index = min(waypoint_index + 1, len(waypoints) - 1)

            # Linear interpolation between waypoints
            if waypoint_index == next_waypoint_index:
                position = waypoints[waypoint_index]
            else:
                local_t = (t * (len(waypoints) - 1)) - waypoint_index
                position = waypoints[waypoint_index].lerp(
                    waypoints[next_waypoint_index], local_t
                )

            # Add realistic forklift movement with vertical motion
            # Forklift moves up and down like real forklift forks
            base_height = 1.6  # Base forklift height
            fork_movement = 0.8  # Fork up/down movement range

            # Create realistic forklift movement pattern
            # Move up when approaching pallets, down when moving away
            movement_phase = (i / num_points) * 2 * math.pi
            vertical_offset = math.sin(movement_phase * 2) * fork_movement

            position.z = base_height + vertical_offset + random.uniform(-0.1, 0.1)

            # Add very small random offset for realistic movement (reduced to avoid obstacles)
            position.x += random.uniform(-0.1, 0.1)
            position.y += random.uniform(-0.1, 0.1)

            # Final collision check with proper obstacle bounds
            if not self.is_position_safe_with_bounds(
                position, all_obstacles, safety_margin
            ):
                # Try to find a nearby safe position with more attempts
                safe_position = self.find_nearby_safe_position_with_bounds(
                    position, all_obstacles, safety_margin, max_attempts=30
                )
                if safe_position:
                    position = safe_position
                else:
                    # Skip this point if no safe position found
                    print(
                        f"⚠️ Skipping unsafe position: ({position.x:.1f}, {position.y:.1f}, {position.z:.1f})"
                    )
                    continue

            # Look towards nearby pallets, but always horizontally
            look_target = self.find_nearest_pallet(position, pallets)
            look_dir = (look_target - position).normalized()
            # Force horizontal look direction (no pitch/roll, only yaw)
            look_dir.z = 0  # Remove vertical component
            look_dir = look_dir.normalized()
            rotation = look_dir.to_track_quat("-Z", "Y").to_euler()

            path.append({"position": position, "rotation": rotation})

        print(f"🎬 Generated {len(path)} camera positions for path")

        return (
            path
            if path
            else [
                {"position": Vector((0, 0, 1.6)), "rotation": Euler((0, 0, 0))},
                {"position": Vector((5, 0, 1.6)), "rotation": Euler((0, 0, 0))},
            ]
        )

    def get_all_obstacles_with_bounds(self, _pallets, _boxes, _collections):
        """Get all obstacles with their proper bounding boxes from left and right collections."""
        obstacles = []

        # Find the left and right collections (which contain rack collections)
        left_collection = None
        right_collection = None

        for collection in bpy.data.collections:
            if collection.name.lower() == "left":
                left_collection = collection
            elif collection.name.lower() == "right":
                right_collection = collection

        if not left_collection and not right_collection:
            print(
                "⚠️ Warning: 'left' and 'right' collections not found, using warehouse collection"
            )
            # Fallback to warehouse collection
            warehouse_collection = None
            for collection in bpy.data.collections:
                if collection.name.lower() == "warehouse":
                    warehouse_collection = collection
                    break

            if warehouse_collection:
                for obj in warehouse_collection.objects:
                    if self.should_avoid_object(obj) and obj and obj.type == "MESH":
                        bbox = self.get_object_bounding_box(obj)
                        obstacles.append(
                            {"object": obj, "bounds": bbox, "center": obj.location}
                        )
            return obstacles

        # Get obstacles from left collection
        if left_collection:
            print(
                f"🏭 Found 'left' collection with {len(left_collection.objects)} objects"
            )
            for obj in left_collection.objects:
                if self.should_avoid_object(obj) and obj and obj.type == "MESH":
                    bbox = self.get_object_bounding_box(obj)
                    obstacles.append(
                        {"object": obj, "bounds": bbox, "center": obj.location}
                    )
                    print(
                        f"   🚧 Avoiding object: {obj.name} (size: {bbox['max_x']-bbox['min_x']:.1f}x{bbox['max_y']-bbox['min_y']:.1f}x{bbox['max_z']-bbox['min_z']:.1f})"
                    )

        # Get obstacles from right collection
        if right_collection:
            print(
                f"🏭 Found 'right' collection with {len(right_collection.objects)} objects"
            )
            for obj in right_collection.objects:
                if self.should_avoid_object(obj) and obj and obj.type == "MESH":
                    bbox = self.get_object_bounding_box(obj)
                    obstacles.append(
                        {"object": obj, "bounds": bbox, "center": obj.location}
                    )
                    print(
                        f"   🚧 Avoiding object: {obj.name} (size: {bbox['max_x']-bbox['min_x']:.1f}x{bbox['max_y']-bbox['min_y']:.1f}x{bbox['max_z']-bbox['min_z']:.1f})"
                    )

        print(f"🚧 Total obstacles to avoid: {len(obstacles)}")
        return obstacles

    def should_avoid_object(self, obj):
        """Check if an object should be avoided in path generation."""
        if not obj or obj.type != "MESH":
            return False

        obj_name_lower = obj.name.lower()

        # Avoid objects that start with "rack" or contain "rack"
        if "rack" in obj_name_lower:
            return True

        # Avoid forklift objects
        if "forklift" in obj_name_lower:
            return True

        # Avoid AMR (Autonomous Mobile Robot) objects
        if "amr" in obj_name_lower:
            return True

        # Avoid other large infrastructure objects
        avoid_keywords = [
            "wall",
            "column",
            "support",
            "beam",
            "structure",
            "shelf",
            "storage",
        ]
        for keyword in avoid_keywords:
            if keyword in obj_name_lower:
                return True

        # Avoid objects that are likely infrastructure based on size
        try:
            bbox = self.get_object_bounding_box(obj)
            width = bbox["max_x"] - bbox["min_x"]
            height = bbox["max_y"] - bbox["min_y"]
            depth = bbox["max_z"] - bbox["min_z"]

            # If object is very large, it's likely infrastructure
            if width > 2.0 or height > 2.0 or depth > 2.0:
                return True
        except Exception:
            pass

        return False

    def get_object_bounding_box(self, obj):
        """Get the world-space bounding box of an object."""
        # Get the object's bounding box in world coordinates
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

        # Calculate min/max coordinates
        min_x = min(corner.x for corner in bbox_corners)
        max_x = max(corner.x for corner in bbox_corners)
        min_y = min(corner.y for corner in bbox_corners)
        max_y = max(corner.y for corner in bbox_corners)
        min_z = min(corner.z for corner in bbox_corners)
        max_z = max(corner.z for corner in bbox_corners)

        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "min_z": min_z,
            "max_z": max_z,
        }

    def calculate_warehouse_bounds(self, obstacles):
        """Calculate the warehouse bounds from obstacle bounding boxes."""
        if not obstacles:
            return {"min_x": -10, "max_x": 10, "min_y": -10, "max_y": 10}

        min_x = min(obs["bounds"]["min_x"] for obs in obstacles)
        max_x = max(obs["bounds"]["max_x"] for obs in obstacles)
        min_y = min(obs["bounds"]["min_y"] for obs in obstacles)
        max_y = max(obs["bounds"]["max_y"] for obs in obstacles)

        # Add some margin around the warehouse
        margin = 5.0
        return {
            "min_x": min_x - margin,
            "max_x": max_x + margin,
            "min_y": min_y - margin,
            "max_y": max_y + margin,
        }

    def generate_realistic_warehouse_path(
        self, obstacles, warehouse_bounds, safety_margin
    ):
        """Generate a realistic warehouse path that goes between left and right collections."""
        waypoints = []

        # Find left and right collections to understand warehouse layout
        left_collection = None
        right_collection = None
        forklift_collection = None

        # Debug: Print all available collections with nested structure
        print("🔍 Available collections in scene:")
        for collection in bpy.data.collections:
            total_objects = len(self.get_all_objects_from_collection(collection))
            print(
                f"   - {collection.name} ({len(collection.objects)} direct objects, {total_objects} total including nested)"
            )
            if collection.objects:
                for obj in collection.objects[:3]:  # Show first 3 direct objects
                    print(f"     * {obj.name} at {obj.location}")
            if collection.children:
                for child in collection.children:
                    len(self.get_all_objects_from_collection(child))

        # More flexible collection detection
        for collection in bpy.data.collections:
            collection_name_lower = collection.name.lower()
            print(
                f"🔍 Checking collection: '{collection.name}' (lowercase: '{collection_name_lower}')"
            )

            if collection_name_lower == "left" or "left" in collection_name_lower:
                left_collection = collection
                print(f"✅ Found LEFT collection: {collection.name}")
            elif collection_name_lower == "right" or "right" in collection_name_lower:
                right_collection = collection
                print(f"✅ Found RIGHT collection: {collection.name}")
            elif "forklift" in collection_name_lower or "fork" in collection_name_lower:
                forklift_collection = collection
                print(f"✅ Found FORKLIFT collection: {collection.name}")

        # If collections not found by name, try to detect them by object naming patterns
        if not left_collection or not right_collection:
            print(
                "⚠️ Collections not found by name, trying to detect by object patterns..."
            )
            (
                left_collection,
                right_collection,
                forklift_collection,
            ) = self.detect_collections_by_objects()

            if not left_collection or not right_collection:
                print("⚠️ Still no collections found, using grid-based pathfinding")
                return self.generate_safe_waypoints_grid(
                    obstacles, warehouse_bounds, safety_margin
                )

        # Calculate collection bounds with detailed object information
        print(
            f"📊 Calculating bounds for LEFT collection: {left_collection.name if left_collection else 'None'}"
        )
        left_bounds = self.get_collection_bounds(left_collection)

        print(
            f"📊 Calculating bounds for RIGHT collection: {right_collection.name if right_collection else 'None'}"
        )
        right_bounds = self.get_collection_bounds(right_collection)

        if forklift_collection:
            print(
                f"📊 Calculating bounds for FORKLIFT collection: {forklift_collection.name}"
            )
            forklift_bounds = self.get_collection_bounds(forklift_collection)
        else:
            print("📊 No forklift collection found")
            forklift_bounds = None

        print(
            f"🏭 Left collection: {left_bounds['object_count']} objects, X({left_bounds['min_x']:.1f} to {left_bounds['max_x']:.1f}), Y({left_bounds['min_y']:.1f} to {left_bounds['max_y']:.1f})"
        )
        print(
            f"🏭 Right collection: {right_bounds['object_count']} objects, X({right_bounds['min_x']:.1f} to {right_bounds['max_x']:.1f}), Y({right_bounds['min_y']:.1f} to {right_bounds['max_y']:.1f})"
        )
        if forklift_bounds:
            print(
                f"🏭 Forklift collection: {forklift_bounds['object_count']} objects, X({forklift_bounds['min_x']:.1f} to {forklift_bounds['max_x']:.1f}), Y({forklift_bounds['min_y']:.1f} to {forklift_bounds['max_y']:.1f})"
            )

        # Print detailed object information
        if left_bounds["objects"]:
            print("   📦 Left collection objects:")
            for obj in left_bounds["objects"][:5]:  # Show first 5 objects
                print(
                    f"      - {obj['name']}: pos({obj['location'][0]:.1f}, {obj['location'][1]:.1f}, {obj['location'][2]:.1f}) size({obj['size']['width']:.1f}x{obj['size']['height']:.1f}x{obj['size']['depth']:.1f})"
                )

        if right_bounds["objects"]:
            print("   📦 Right collection objects:")
            for obj in right_bounds["objects"][:5]:  # Show first 5 objects
                print(
                    f"      - {obj['name']}: pos({obj['location'][0]:.1f}, {obj['location'][1]:.1f}, {obj['location'][2]:.1f}) size({obj['size']['width']:.1f}x{obj['size']['height']:.1f}x{obj['size']['depth']:.1f})"
                )

        # Create systematic warehouse scanning path based on collection boundaries
        aisle_width = 3.0  # Distance from collection boundary
        scan_spacing = 2.5  # Distance between scan lines
        vertical_movement = 0.8  # Up/down movement range

        # Calculate collection boundaries
        left_min_x = left_bounds["min_x"]
        left_max_x = left_bounds["max_x"]
        left_min_y = left_bounds["min_y"]
        left_max_y = left_bounds["max_y"]

        right_min_x = right_bounds["min_x"]
        right_max_x = right_bounds["max_x"]
        right_min_y = right_bounds["min_y"]
        right_max_y = right_bounds["max_y"]

        # Calculate overall warehouse bounds
        warehouse_min_y = min(left_min_y, right_min_y)
        warehouse_max_y = max(left_max_y, right_max_y)
        warehouse_length = warehouse_max_y - warehouse_min_y

        # Define scanning positions
        # Right collection scanning positions
        right_front_x = right_min_x - aisle_width  # In front of right collection
        right_back_x = right_max_x + aisle_width  # Behind right collection

        # Left collection scanning positions
        left_front_x = left_max_x + aisle_width  # In front of left collection
        left_back_x = left_min_x - aisle_width  # Behind left collection

        # Center position between collections
        center_x = (left_max_x + right_min_x) / 2

        # Start position (initial camera position)
        start_y = warehouse_min_y - aisle_width
        start_z = 1.6

        print(
            f"📊 Warehouse bounds: Y({warehouse_min_y:.1f} to {warehouse_max_y:.1f}), Length: {warehouse_length:.1f}"
        )
        print(
            f"📊 Right collection: X({right_min_x:.1f} to {right_max_x:.1f}), Y({right_min_y:.1f} to {right_max_y:.1f})"
        )
        print(
            f"📊 Left collection: X({left_min_x:.1f} to {left_max_x:.1f}), Y({left_min_y:.1f} to {left_max_y:.1f})"
        )
        print(
            f"📊 Scanning positions: Right front({right_front_x:.1f}), Right back({right_back_x:.1f}), Left front({left_front_x:.1f}), Left back({left_back_x:.1f})"
        )

        # Start position (initial camera position)
        start_waypoint = Vector((center_x, start_y, start_z))
        if self.is_position_safe_with_bounds(start_waypoint, obstacles, safety_margin):
            waypoints.append(start_waypoint)

        # Create systematic scanning path
        path_points = []

        # 1. Start at initial position
        path_points.append((center_x, start_y, start_z))

        # 2. SCAN RIGHT COLLECTION - Front side
        print("🔄 Starting right collection front scan...")
        num_scan_lines = max(3, int(warehouse_length / scan_spacing))

        for i in range(num_scan_lines + 1):
            y_pos = warehouse_min_y + (i * scan_spacing)
            if y_pos <= warehouse_max_y:
                # Add vertical movement (up/down) without camera rotation
                vertical_offset = math.sin(i * 0.5) * vertical_movement
                z_pos = start_z + vertical_offset
                path_points.append((right_front_x, y_pos, z_pos))
                print(f"   📍 Right front scan: Y({y_pos:.1f}), Z({z_pos:.1f})")

        # 3. Turn to back side of right collection
        path_points.append((right_back_x, warehouse_max_y, start_z))
        print("🔄 Turning to right collection back side...")

        # 4. SCAN RIGHT COLLECTION - Back side
        print("🔄 Starting right collection back scan...")
        for i in range(num_scan_lines + 1):
            y_pos = warehouse_max_y - (i * scan_spacing)
            if y_pos >= warehouse_min_y:
                # Add vertical movement (up/down) without camera rotation
                vertical_offset = (
                    math.sin((num_scan_lines - i) * 0.5) * vertical_movement
                )
                z_pos = start_z + vertical_offset
                path_points.append((right_back_x, y_pos, z_pos))
                print(f"   📍 Right back scan: Y({y_pos:.1f}), Z({z_pos:.1f})")

        # 5. Move to center and then to left collection
        path_points.append((center_x, warehouse_min_y, start_z))
        print("🔄 Moving to left collection...")

        # 6. SCAN LEFT COLLECTION - Front side
        print("🔄 Starting left collection front scan...")
        for i in range(num_scan_lines + 1):
            y_pos = warehouse_min_y + (i * scan_spacing)
            if y_pos <= warehouse_max_y:
                # Add vertical movement (up/down) without camera rotation
                vertical_offset = math.sin(i * 0.5) * vertical_movement
                z_pos = start_z + vertical_offset
                path_points.append((left_front_x, y_pos, z_pos))
                print(f"   📍 Left front scan: Y({y_pos:.1f}), Z({z_pos:.1f})")

        # 7. Turn to back side of left collection
        path_points.append((left_back_x, warehouse_max_y, start_z))
        print("🔄 Turning to left collection back side...")

        # 8. SCAN LEFT COLLECTION - Back side
        print("🔄 Starting left collection back scan...")
        for i in range(num_scan_lines + 1):
            y_pos = warehouse_max_y - (i * scan_spacing)
            if y_pos >= warehouse_min_y:
                # Add vertical movement (up/down) without camera rotation
                vertical_offset = (
                    math.sin((num_scan_lines - i) * 0.5) * vertical_movement
                )
                z_pos = start_z + vertical_offset
                path_points.append((left_back_x, y_pos, z_pos))
                print(f"   📍 Left back scan: Y({y_pos:.1f}), Z({z_pos:.1f})")

        # 9. Return to initial position
        path_points.append((center_x, start_y, start_z))
        print("🔄 Returning to initial position...")

        # Add all waypoints with safety checks
        for point in path_points:
            waypoint = Vector(point)

            # Check if position is safe
            if self.is_position_safe_with_bounds(waypoint, obstacles, safety_margin):
                waypoints.append(waypoint)
            else:
                # Try to find nearby safe position
                safe_pos = self.find_nearby_safe_position_with_bounds(
                    waypoint, obstacles, safety_margin, max_attempts=10
                )
                if safe_pos:
                    waypoints.append(safe_pos)
                else:
                    # Add original point if no safe position found
                    waypoints.append(waypoint)

        # Add return path to start position
        if waypoints:
            return_waypoint = Vector((center_x, start_y, start_z))
            if self.is_position_safe_with_bounds(
                return_waypoint, obstacles, safety_margin
            ):
                waypoints.append(return_waypoint)

        print(f"🛤️ Generated {len(waypoints)} waypoints for realistic warehouse path")
        return waypoints

    def get_collection_bounds(self, collection):
        """Get the bounding box of a collection with detailed object information using accurate world coordinates."""
        if not collection:
            print("⚠️ Collection is None")
            return {
                "min_x": 0,
                "max_x": 0,
                "min_y": 0,
                "max_y": 0,
                "min_z": 0,
                "max_z": 0,
                "objects": [],
                "object_count": 0,
            }

        print(
            f"📊 Analyzing collection '{collection.name}' (including all nested sub-collections)"
        )

        # Get all objects from this collection and all nested collections
        all_objects = self.get_all_objects_from_collection(collection)

        if not all_objects:
            print(
                f"⚠️ Collection '{collection.name}' has no objects (including nested collections)"
            )
            return {
                "min_x": 0,
                "max_x": 0,
                "min_y": 0,
                "max_y": 0,
                "min_z": 0,
                "max_z": 0,
                "objects": [],
                "object_count": 0,
            }

        print(
            f"📊 Found {len(all_objects)} total objects in collection '{collection.name}' (including nested)"
        )
        objects_info = []

        for obj in all_objects:
            if obj.type == "MESH" and obj.visible_get():
                try:
                    # Get object's bounding box in local coordinates
                    bbox_corners = [
                        obj.matrix_world @ Vector(corner) for corner in obj.bound_box
                    ]

                    # Calculate world bounds from transformed corners
                    obj_min_x = min(corner.x for corner in bbox_corners)
                    obj_max_x = max(corner.x for corner in bbox_corners)
                    obj_min_y = min(corner.y for corner in bbox_corners)
                    obj_max_y = max(corner.y for corner in bbox_corners)
                    obj_min_z = min(corner.z for corner in bbox_corners)
                    obj_max_z = max(corner.z for corner in bbox_corners)

                    # Calculate dimensions
                    width = obj_max_x - obj_min_x
                    height = obj_max_y - obj_min_y
                    depth = obj_max_z - obj_min_z

                    print(
                        f"   📦 {obj.name}: X({obj_min_x:.2f} to {obj_max_x:.2f}), Y({obj_min_y:.2f} to {obj_max_y:.2f}), Z({obj_min_z:.2f} to {obj_max_z:.2f})"
                    )
                    print(f"      Size: {width:.2f} x {height:.2f} x {depth:.2f}")

                    objects_info.append(
                        {
                            "name": obj.name,
                            "location": [
                                obj.location.x,
                                obj.location.y,
                                obj.location.z,
                            ],
                            "bounds": {
                                "min_x": obj_min_x,
                                "max_x": obj_max_x,
                                "min_y": obj_min_y,
                                "max_y": obj_max_y,
                                "min_z": obj_min_z,
                                "max_z": obj_max_z,
                            },
                            "size": {
                                "width": width,
                                "height": height,
                                "depth": depth,
                            },
                        }
                    )
                except Exception as e:
                    print(f"   ⚠️ Error processing object {obj.name}: {e}")
                    # Fallback to simple bounds using location
                    objects_info.append(
                        {
                            "name": obj.name,
                            "location": [
                                obj.location.x,
                                obj.location.y,
                                obj.location.z,
                            ],
                            "bounds": {
                                "min_x": obj.location.x - 0.5,
                                "max_x": obj.location.x + 0.5,
                                "min_y": obj.location.y - 0.5,
                                "max_y": obj.location.y + 0.5,
                                "min_z": obj.location.z - 0.5,
                                "max_z": obj.location.z + 0.5,
                            },
                            "size": {"width": 1.0, "height": 1.0, "depth": 1.0},
                        }
                    )

        # Calculate overall collection bounds
        if objects_info:
            min_x = min(obj["bounds"]["min_x"] for obj in objects_info)
            max_x = max(obj["bounds"]["max_x"] for obj in objects_info)
            min_y = min(obj["bounds"]["min_y"] for obj in objects_info)
            max_y = max(obj["bounds"]["max_y"] for obj in objects_info)
            min_z = min(obj["bounds"]["min_z"] for obj in objects_info)
            max_z = max(obj["bounds"]["max_z"] for obj in objects_info)
        else:
            min_x = max_x = min_y = max_y = min_z = max_z = 0

        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "min_z": min_z,
            "max_z": max_z,
            "objects": objects_info,
            "object_count": len(objects_info),
        }

    def detect_collections_by_objects(self):
        """
        Detect left and right collections by analyzing object positions and naming patterns.
        This is a fallback method when collections are not found by name.
        """
        print("🔍 Detecting collections by object analysis...")

        # Get all mesh objects
        all_objects = [
            obj for obj in bpy.data.objects if obj.type == "MESH" and obj.visible_get()
        ]

        if not all_objects:
            print("⚠️ No mesh objects found in scene")
            return None, None, None

        # Analyze object positions
        left_objects = []
        right_objects = []
        forklift_objects = []

        # Calculate center X position of all objects
        all_x_positions = [obj.location.x for obj in all_objects]
        center_x = sum(all_x_positions) / len(all_x_positions)

        print(f"📊 Scene center X position: {center_x:.2f}")

        # Categorize objects by position and name
        for obj in all_objects:
            obj_name_lower = obj.name.lower()
            obj_x = obj.location.x

            # Check for forklift objects by name
            if any(
                keyword in obj_name_lower
                for keyword in ["forklift", "fork", "lift", "vehicle"]
            ):
                forklift_objects.append(obj)
                print(f"   🚛 Forklift object: {obj.name} at X={obj_x:.2f}")
            # Categorize by X position
            elif obj_x < center_x - 1.0:  # Left side (with margin)
                left_objects.append(obj)
                print(f"   ⬅️ Left object: {obj.name} at X={obj_x:.2f}")
            elif obj_x > center_x + 1.0:  # Right side (with margin)
                right_objects.append(obj)
                print(f"   ➡️ Right object: {obj.name} at X={obj_x:.2f}")
            else:
                print(f"   ⚪ Center object: {obj.name} at X={obj_x:.2f}")

        print(
            f"📊 Detected: {len(left_objects)} left objects, {len(right_objects)} right objects, {len(forklift_objects)} forklift objects"
        )

        # Create virtual collections if we have enough objects
        left_collection = None
        right_collection = None
        forklift_collection = None

        if (
            len(left_objects) >= 3
        ):  # Need at least 3 objects to consider it a collection
            left_collection = type(
                "Collection", (), {"name": "Detected_Left", "objects": left_objects}
            )()
            print(f"✅ Created virtual LEFT collection with {len(left_objects)} objects")

        if (
            len(right_objects) >= 3
        ):  # Need at least 3 objects to consider it a collection
            right_collection = type(
                "Collection", (), {"name": "Detected_Right", "objects": right_objects}
            )()
            print(
                f"✅ Created virtual RIGHT collection with {len(right_objects)} objects"
            )

        if len(forklift_objects) >= 1:  # Even 1 forklift object is useful
            forklift_collection = type(
                "Collection",
                (),
                {"name": "Detected_Forklift", "objects": forklift_objects},
            )()
            print(
                f"✅ Created virtual FORKLIFT collection with {len(forklift_objects)} objects"
            )

        return left_collection, right_collection, forklift_collection

    def get_all_objects_from_collection(self, collection):
        """
        Recursively get all objects from a collection and all its nested sub-collections.
        This ensures we capture objects in deeply nested collection hierarchies.
        """
        all_objects = []

        # Add direct objects from this collection
        for obj in collection.objects:
            all_objects.append(obj)

        # Recursively add objects from child collections
        for child_collection in collection.children:
            child_objects = self.get_all_objects_from_collection(child_collection)
            all_objects.extend(child_objects)

        return all_objects

    def plot_warehouse_structure(self, ax, warehouse_bounds):
        """Plot warehouse floor and walls."""
        # Plot warehouse floor
        floor_x = [
            warehouse_bounds["min_x"],
            warehouse_bounds["max_x"],
            warehouse_bounds["max_x"],
            warehouse_bounds["min_x"],
            warehouse_bounds["min_x"],
        ]
        floor_y = [
            warehouse_bounds["min_y"],
            warehouse_bounds["min_y"],
            warehouse_bounds["max_y"],
            warehouse_bounds["max_y"],
            warehouse_bounds["min_y"],
        ]
        floor_z = [0, 0, 0, 0, 0]

        ax.plot(
            floor_x,
            floor_y,
            floor_z,
            "k-",
            linewidth=2,
            alpha=0.3,
            label="Warehouse Floor",
        )

        # Plot warehouse walls
        wall_height = 4.0

        # Bottom wall (Y = min_y)
        wall_bottom_x = [warehouse_bounds["min_x"], warehouse_bounds["max_x"]]
        wall_bottom_y = [warehouse_bounds["min_y"], warehouse_bounds["min_y"]]
        wall_bottom_z = [0, 0]
        wall_bottom_z_top = [wall_height, wall_height]
        ax.plot(
            wall_bottom_x, wall_bottom_y, wall_bottom_z, "k-", linewidth=2, alpha=0.5
        )
        ax.plot(
            wall_bottom_x,
            wall_bottom_y,
            wall_bottom_z_top,
            "k-",
            linewidth=2,
            alpha=0.5,
        )
        for i in range(len(wall_bottom_x)):
            ax.plot(
                [wall_bottom_x[i], wall_bottom_x[i]],
                [wall_bottom_y[i], wall_bottom_y[i]],
                [wall_bottom_z[i], wall_bottom_z_top[i]],
                "k-",
                linewidth=2,
                alpha=0.5,
            )

        # Top wall (Y = max_y)
        wall_top_x = [warehouse_bounds["min_x"], warehouse_bounds["max_x"]]
        wall_top_y = [warehouse_bounds["max_y"], warehouse_bounds["max_y"]]
        wall_top_z = [0, 0]
        wall_top_z_top = [wall_height, wall_height]
        ax.plot(wall_top_x, wall_top_y, wall_top_z, "k-", linewidth=2, alpha=0.5)
        ax.plot(wall_top_x, wall_top_y, wall_top_z_top, "k-", linewidth=2, alpha=0.5)
        for i in range(len(wall_top_x)):
            ax.plot(
                [wall_top_x[i], wall_top_x[i]],
                [wall_top_y[i], wall_top_y[i]],
                [wall_top_z[i], wall_top_z_top[i]],
                "k-",
                linewidth=2,
                alpha=0.5,
            )

        # Left wall (X = min_x)
        wall_left_x = [warehouse_bounds["min_x"], warehouse_bounds["min_x"]]
        wall_left_y = [warehouse_bounds["min_y"], warehouse_bounds["max_y"]]
        wall_left_z = [0, 0]
        wall_left_z_top = [wall_height, wall_height]
        ax.plot(wall_left_x, wall_left_y, wall_left_z, "k-", linewidth=2, alpha=0.5)
        ax.plot(wall_left_x, wall_left_y, wall_left_z_top, "k-", linewidth=2, alpha=0.5)
        for i in range(len(wall_left_x)):
            ax.plot(
                [wall_left_x[i], wall_left_x[i]],
                [wall_left_y[i], wall_left_y[i]],
                [wall_left_z[i], wall_left_z_top[i]],
                "k-",
                linewidth=2,
                alpha=0.5,
            )

        # Right wall (X = max_x)
        wall_right_x = [warehouse_bounds["max_x"], warehouse_bounds["max_x"]]
        wall_right_y = [warehouse_bounds["min_y"], warehouse_bounds["max_y"]]
        wall_right_z = [0, 0]
        wall_right_z_top = [wall_height, wall_height]
        ax.plot(wall_right_x, wall_right_y, wall_right_z, "k-", linewidth=2, alpha=0.5)
        ax.plot(
            wall_right_x, wall_right_y, wall_right_z_top, "k-", linewidth=2, alpha=0.5
        )
        for i in range(len(wall_right_x)):
            ax.plot(
                [wall_right_x[i], wall_right_x[i]],
                [wall_right_y[i], wall_right_y[i]],
                [wall_right_z[i], wall_right_z_top[i]],
                "k-",
                linewidth=2,
                alpha=0.5,
            )

    def generate_safe_waypoints_grid(self, obstacles, warehouse_bounds, safety_margin):
        """Generate safe waypoints using grid-based pathfinding."""
        waypoints = []

        # Create a fine grid for pathfinding
        grid_resolution = 0.5  # 0.5m grid resolution
        min_x = warehouse_bounds["min_x"]
        max_x = warehouse_bounds["max_x"]
        min_y = warehouse_bounds["min_y"]
        max_y = warehouse_bounds["max_y"]

        # Calculate grid dimensions
        width = int((max_x - min_x) / grid_resolution) + 1
        height = int((max_y - min_y) / grid_resolution) + 1

        # Create grid (0 = free, 1 = obstacle)
        grid = [[0 for _ in range(width)] for _ in range(height)]

        # Mark obstacles in grid
        for obs in obstacles:
            bounds = obs["bounds"]
            # Expand obstacle bounds by safety margin
            obs_min_x = bounds["min_x"] - safety_margin
            obs_max_x = bounds["max_x"] + safety_margin
            obs_min_y = bounds["min_y"] - safety_margin
            obs_max_y = bounds["max_y"] + safety_margin

            # Convert to grid coordinates
            grid_min_x = max(0, int((obs_min_x - min_x) / grid_resolution))
            grid_max_x = min(width - 1, int((obs_max_x - min_x) / grid_resolution))
            grid_min_y = max(0, int((obs_min_y - min_y) / grid_resolution))
            grid_max_y = min(height - 1, int((obs_max_y - min_y) / grid_resolution))

            # Mark obstacle cells
            for x in range(grid_min_x, grid_max_x + 1):
                for y in range(grid_min_y, grid_max_y + 1):
                    grid[y][x] = 1

        print(f"🗺️ Created {width}x{height} grid with {len(obstacles)} obstacles")

        # Find safe waypoints using A* pathfinding
        start_x, start_y = 0, 0
        end_x, end_y = width - 1, height - 1

        # Make sure start and end are free
        while grid[start_y][start_x] == 1 and start_x < width - 1:
            start_x += 1
        while grid[start_y][start_x] == 1 and start_y < height - 1:
            start_y += 1

        while grid[end_y][end_x] == 1 and end_x > 0:
            end_x -= 1
        while grid[end_y][end_x] == 1 and end_y > 0:
            end_y -= 1

        # A* pathfinding
        path = self.astar_pathfinding(grid, (start_x, start_y), (end_x, end_y))

        if not path:
            # Fallback: create simple path along edges
            path = self.create_fallback_path(grid, width, height)

        # Convert grid coordinates back to world coordinates
        for x, y in path:
            world_x = min_x + x * grid_resolution
            world_y = min_y + y * grid_resolution
            waypoints.append(Vector((world_x, world_y, 1.6)))

        print(f"🛤️ Generated {len(waypoints)} waypoints using A* pathfinding")
        return waypoints

    def astar_pathfinding(self, grid, start, goal):
        """A* pathfinding algorithm implementation."""

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def get_neighbors(pos):
            x, y = pos
            neighbors = []
            # 8-directional movement
            for dx, dy in [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0:
                    neighbors.append((nx, ny))
            return neighbors

        open_set = [start]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}

        while open_set:
            current = min(open_set, key=lambda x: f_score.get(x, float("inf")))
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            open_set.remove(current)

            for neighbor in get_neighbors(current):
                tentative_g_score = g_score[current] + 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + heuristic(neighbor, goal)

                    if neighbor not in open_set:
                        open_set.append(neighbor)

        return []  # No path found

    def create_fallback_path(self, grid, width, height):
        """Create a fallback path along the edges if A* fails."""
        path = []

        # Try to find a path along the perimeter
        # Top edge
        for x in range(0, width, 2):
            if grid[0][x] == 0:
                path.append((x, 0))

        # Right edge
        for y in range(0, height, 2):
            if grid[y][width - 1] == 0:
                path.append((width - 1, y))

        # Bottom edge
        for x in range(width - 1, -1, -2):
            if grid[height - 1][x] == 0:
                path.append((x, height - 1))

        # Left edge
        for y in range(height - 1, -1, -2):
            if grid[y][0] == 0:
                path.append((0, y))

        if not path:
            # Last resort: just use corners
            path = [(0, 0), (width - 1, height - 1)]

        return path

    def generate_and_save_path_visualization(
        self, camera_path, obstacles, warehouse_bounds, scene_id=0
    ):
        """Generate and save 3D path visualization to debug_3d/paths/ for each scene."""
        try:
            import matplotlib.pyplot as plt

            # Create paths folder in debug_3d (inside output warehouse batch folder)
            paths_folder = Path(self.paths["debug_3d"]) / "paths"
            paths_folder.mkdir(parents=True, exist_ok=True)

            # Create 3D plot
            fig = plt.figure(figsize=(15, 12))
            ax = fig.add_subplot(111, projection="3d")

            # Plot warehouse collections as shapes
            self.plot_warehouse_collections(ax)

            # Plot obstacles with more detail
            if obstacles:
                for obs in obstacles:
                    bounds = obs["bounds"]
                    self.plot_obstacle_box(ax, bounds, obs["object"].name)

            # Plot warehouse floor and walls
            self.plot_warehouse_structure(ax, warehouse_bounds)

            # Plot path
            if camera_path:
                path_x = [p["position"].x for p in camera_path]
                path_y = [p["position"].y for p in camera_path]
                path_z = [p["position"].z for p in camera_path]

                # Plot path line with gradient colors
                for i in range(len(path_x) - 1):
                    alpha = 0.3 + 0.7 * (i / (len(path_x) - 1))
                    ax.plot(
                        path_x[i : i + 2],
                        path_y[i : i + 2],
                        path_z[i : i + 2],
                        "b-",
                        linewidth=3,
                        alpha=alpha,
                    )

                # Plot path points
                ax.scatter(path_x, path_y, path_z, c="blue", s=50, alpha=0.8)

                # Mark start and end
                ax.scatter(
                    path_x[0],
                    path_y[0],
                    path_z[0],
                    c="green",
                    s=200,
                    marker="o",
                    label="Start",
                    edgecolors="black",
                )
                ax.scatter(
                    path_x[-1],
                    path_y[-1],
                    path_z[-1],
                    c="red",
                    s=200,
                    marker="s",
                    label="End",
                    edgecolors="black",
                )

            # Set labels and title
            ax.set_xlabel("X (m)", fontsize=12)
            ax.set_ylabel("Y (m)", fontsize=12)
            ax.set_zlabel("Z (m)", fontsize=12)
            ax.set_title(
                "Warehouse Camera Path with Collections", fontsize=14, fontweight="bold"
            )
            ax.legend(fontsize=10)

            # Set equal aspect ratio
            max_range = max(
                warehouse_bounds["max_x"] - warehouse_bounds["min_x"],
                warehouse_bounds["max_y"] - warehouse_bounds["min_y"],
                5.0,  # Z range
            )
            mid_x = (warehouse_bounds["max_x"] + warehouse_bounds["min_x"]) / 2
            mid_y = (warehouse_bounds["max_y"] + warehouse_bounds["min_y"]) / 2

            ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
            ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
            ax.set_zlim(0, 5)

            # Save plot with scene-specific filename directly in paths folder
            plot_filename = f"warehouse_camera_path_scene_{scene_id + 1:03d}_3d.png"
            plot_path = paths_folder / plot_filename
            plt.savefig(plot_path, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close()

            print(f"📊 Saved 3D path visualization: {plot_path}")

        except Exception as e:
            print(f"❌ Error generating path visualization: {e}")

    def plot_warehouse_collections(self, ax):
        """Plot warehouse collections as colored shapes with individual objects using the same detection logic as path generation."""
        print("🎨 Plotting warehouse collections...")

        # Use the same collection detection logic as path generation
        left_collection = None
        right_collection = None
        forklift_collection = None

        # More flexible collection detection (same as in path generation)
        for collection in bpy.data.collections:
            collection_name_lower = collection.name.lower()
            if collection_name_lower == "left" or "left" in collection_name_lower:
                left_collection = collection
            elif collection_name_lower == "right" or "right" in collection_name_lower:
                right_collection = collection
            elif "forklift" in collection_name_lower or "fork" in collection_name_lower:
                forklift_collection = collection

        # If collections not found by name, try to detect them by object patterns
        if not left_collection or not right_collection:
            (
                left_collection,
                right_collection,
                forklift_collection,
            ) = self.detect_collections_by_objects()

        # Plot left collection (collection shape only, no individual objects)
        if left_collection:
            bounds = self.get_collection_bounds(left_collection)
            self.plot_collection_box(
                ax,
                bounds,
                f"Left Collection ({bounds['object_count']} objects)",
                "red",
                0.3,
            )
        else:
            print("   ⚠️ No LEFT collection found for plotting")

        # Plot right collection (collection shape only, no individual objects)
        if right_collection:
            print(f"   🎨 Plotting RIGHT collection: {right_collection.name}")
            bounds = self.get_collection_bounds(right_collection)
            self.plot_collection_box(
                ax,
                bounds,
                f"Right Collection ({bounds['object_count']} objects)",
                "blue",
                0.3,
            )
        else:
            print("   ⚠️ No RIGHT collection found for plotting")

        # Plot forklift collection (collection shape only, no individual objects)
        if forklift_collection:
            print(f"   🎨 Plotting FORKLIFT collection: {forklift_collection.name}")
            bounds = self.get_collection_bounds(forklift_collection)
            self.plot_collection_box(
                ax,
                bounds,
                f"Forklift Collection ({bounds['object_count']} objects)",
                "green",
                0.3,
            )
            # Don't plot individual objects - only show collection boundary
            print(
                f"   📦 Forklift collection bounds: X({bounds['min_x']:.1f} to {bounds['max_x']:.1f}), Y({bounds['min_y']:.1f} to {bounds['max_y']:.1f})"
            )
        else:
            print("   ⚠️ No FORKLIFT collection found for plotting")

    def plot_collection_box(self, ax, bounds, label, color, alpha):
        """Plot a collection as a 3D box."""
        # Create box vertices
        x = [
            bounds["min_x"],
            bounds["max_x"],
            bounds["max_x"],
            bounds["min_x"],
            bounds["min_x"],
        ]
        y = [
            bounds["min_y"],
            bounds["min_y"],
            bounds["max_y"],
            bounds["max_y"],
            bounds["min_y"],
        ]
        z_bottom = [
            bounds["min_z"],
            bounds["min_z"],
            bounds["min_z"],
            bounds["min_z"],
            bounds["min_z"],
        ]
        z_top = [
            bounds["max_z"],
            bounds["max_z"],
            bounds["max_z"],
            bounds["max_z"],
            bounds["max_z"],
        ]

        # Plot bottom face
        ax.plot(x, y, z_bottom, color=color, linewidth=2, alpha=alpha, label=label)
        # Plot top face
        ax.plot(x, y, z_top, color=color, linewidth=2, alpha=alpha)
        # Plot vertical edges
        for i in range(4):
            ax.plot(
                [x[i], x[i]],
                [y[i], y[i]],
                [z_bottom[i], z_top[i]],
                color=color,
                linewidth=2,
                alpha=alpha,
            )

    def plot_obstacle_box(self, ax, bounds, _name):
        """Plot an obstacle as a 3D box."""
        # Create box vertices
        x = [
            bounds["min_x"],
            bounds["max_x"],
            bounds["max_x"],
            bounds["min_x"],
            bounds["min_x"],
        ]
        y = [
            bounds["min_y"],
            bounds["min_y"],
            bounds["max_y"],
            bounds["max_y"],
            bounds["min_y"],
        ]
        z_bottom = [
            bounds["min_z"],
            bounds["min_z"],
            bounds["min_z"],
            bounds["min_z"],
            bounds["min_z"],
        ]
        z_top = [
            bounds["max_z"],
            bounds["max_z"],
            bounds["max_z"],
            bounds["max_z"],
            bounds["max_z"],
        ]

        # Plot as semi-transparent gray boxes
        ax.plot(x, y, z_bottom, "k-", linewidth=1, alpha=0.2)
        ax.plot(x, y, z_top, "k-", linewidth=1, alpha=0.2)
        for i in range(4):
            ax.plot(
                [x[i], x[i]],
                [y[i], y[i]],
                [z_bottom[i], z_top[i]],
                "k-",
                linewidth=1,
                alpha=0.2,
            )

    def plot_object_box(self, ax, obj_info, color, alpha):
        """Plot an individual object as a detailed 3D box with proper wireframe."""
        bounds = obj_info["bounds"]
        size = obj_info["size"]

        # Only plot objects that are large enough to be visible
        if size["width"] < 0.1 or size["height"] < 0.1 or size["depth"] < 0.1:
            return

        # Create all 8 vertices of the bounding box
        vertices = [
            [bounds["min_x"], bounds["min_y"], bounds["min_z"]],  # 0: min corner
            [bounds["max_x"], bounds["min_y"], bounds["min_z"]],  # 1: +X
            [bounds["max_x"], bounds["max_y"], bounds["min_z"]],  # 2: +X+Y
            [bounds["min_x"], bounds["max_y"], bounds["min_z"]],  # 3: +Y
            [bounds["min_x"], bounds["min_y"], bounds["max_z"]],  # 4: +Z
            [bounds["max_x"], bounds["min_y"], bounds["max_z"]],  # 5: +X+Z
            [bounds["max_x"], bounds["max_y"], bounds["max_z"]],  # 6: +X+Y+Z
            [bounds["min_x"], bounds["max_y"], bounds["max_z"]],  # 7: +Y+Z
        ]

        # Define the 12 edges of the box
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

        # Plot all edges
        for edge in edges:
            start, end = edge
            ax.plot(
                [vertices[start][0], vertices[end][0]],
                [vertices[start][1], vertices[end][1]],
                [vertices[start][2], vertices[end][2]],
                color=color,
                alpha=alpha,
                linewidth=0.8,
            )

    def is_position_safe_with_bounds(self, position, obstacles, safety_margin):
        """Check if a position is safe using proper bounding box collision detection."""
        for obstacle in obstacles:
            bounds = obstacle["bounds"]

            # Check if position is within the expanded bounding box
            if (
                bounds["min_x"] - safety_margin
                <= position.x
                <= bounds["max_x"] + safety_margin
                and bounds["min_y"] - safety_margin
                <= position.y
                <= bounds["max_y"] + safety_margin
                and bounds["min_z"] - safety_margin
                <= position.z
                <= bounds["max_z"] + safety_margin
            ):
                return False

        return True

    def find_nearby_safe_position_with_bounds(
        self, position, obstacles, safety_margin, max_attempts=20
    ):
        """Find a nearby safe position using proper bounding box collision detection."""
        for attempt in range(max_attempts):
            # Try positions in a spiral pattern around the original position
            angle = (attempt * 2 * math.pi) / max_attempts
            radius = safety_margin + (attempt * 0.5)

            offset_x = radius * math.cos(angle)
            offset_y = radius * math.sin(angle)

            test_position = Vector(
                (position.x + offset_x, position.y + offset_y, position.z)
            )

            if self.is_position_safe_with_bounds(
                test_position, obstacles, safety_margin
            ):
                return test_position

        return None

    def create_camera_path_visualization(self, camera_path, scene_id):
        """
        Create a visual representation of the camera path in the scene.
        Returns the created objects so they can be removed later.
        """
        if not camera_path or len(camera_path) < 2:
            return []

        created_objects = []

        try:
            # Create a dedicated collection for the camera path
            collection_name = f"CameraPath_Scene{scene_id}"
            path_collection = bpy.data.collections.new(collection_name)
            # Add to the main Scene Collection (root collection)
            bpy.context.scene.collection.children.link(path_collection)

            # Create a curve for the path
            curve_data = bpy.data.curves.new(
                name=f"CameraPath_Scene{scene_id}", type="CURVE"
            )
            curve_data.dimensions = "3D"
            curve_data.resolution_u = 2

            # Create a spline
            spline = curve_data.splines.new("NURBS")
            spline.points.add(
                len(camera_path) - 1
            )  # -1 because one point already exists

            # Set the points
            for i, point_data in enumerate(camera_path):
                position = point_data["position"]
                spline.points[i].co = (position.x, position.y, position.z, 1.0)

            # Create the curve object
            curve_obj = bpy.data.objects.new(f"CameraPath_Scene{scene_id}", curve_data)
            path_collection.objects.link(curve_obj)  # Add to path collection
            created_objects.append(curve_obj)

            # Set curve properties for better visibility
            curve_obj.data.bevel_depth = 0.05
            curve_obj.data.bevel_resolution = 4

            # Create material for the path
            mat = bpy.data.materials.new(name=f"PathMaterial_Scene{scene_id}")
            mat.use_nodes = True
            mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (
                1,
                0,
                0,
                1,
            )  # Red color
            mat.node_tree.nodes["Principled BSDF"].inputs[
                18
            ].default_value = 1.0  # Emission strength
            curve_obj.data.materials.append(mat)

            # Create camera position markers
            for i, point_data in enumerate(camera_path):
                # Create a small sphere for each camera position
                bpy.ops.mesh.primitive_uv_sphere_add(
                    radius=0.1, location=point_data["position"]
                )
                marker_obj = bpy.context.active_object
                marker_obj.name = f"CameraMarker_{scene_id}_{i}"

                # Move marker to path collection
                bpy.context.collection.objects.unlink(marker_obj)
                path_collection.objects.link(marker_obj)
                created_objects.append(marker_obj)

                # Create material for markers
                marker_mat = bpy.data.materials.new(
                    name=f"MarkerMaterial_Scene{scene_id}_{i}"
                )
                marker_mat.use_nodes = True
                marker_mat.node_tree.nodes["Principled BSDF"].inputs[
                    0
                ].default_value = (
                    0,
                    1,
                    0,
                    1,
                )  # Green color
                marker_mat.node_tree.nodes["Principled BSDF"].inputs[
                    18
                ].default_value = 1.0  # Emission strength
                marker_obj.data.materials.append(marker_mat)

                # Add camera direction indicator (small arrow)
                bpy.ops.mesh.primitive_cone_add(
                    radius1=0.05, depth=0.2, location=point_data["position"]
                )
                arrow_obj = bpy.context.active_object
                arrow_obj.name = f"CameraDirection_{scene_id}_{i}"

                # Move arrow to path collection
                bpy.context.collection.objects.unlink(arrow_obj)
                path_collection.objects.link(arrow_obj)

                # Rotate arrow to match camera direction
                rotation = point_data["rotation"]
                arrow_obj.rotation_euler = rotation
                created_objects.append(arrow_obj)

                # Create material for arrows
                arrow_mat = bpy.data.materials.new(
                    name=f"ArrowMaterial_Scene{scene_id}_{i}"
                )
                arrow_mat.use_nodes = True
                arrow_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (
                    0,
                    0,
                    1,
                    1,
                )  # Blue color
                arrow_mat.node_tree.nodes["Principled BSDF"].inputs[
                    18
                ].default_value = 1.0  # Emission strength
                arrow_obj.data.materials.append(arrow_mat)

            print(f"✅ Created camera path visualization with {len(camera_path)} points")
            return created_objects

        except Exception as e:
            print(f"❌ Error creating camera path visualization: {e}")
            # Clean up any partially created objects
            for obj in created_objects:
                with contextlib.suppress(Exception):
                    bpy.data.objects.remove(obj, do_unlink=True)
            return []

    def hide_camera_path_visualization(self, created_objects):
        """
        Hide the camera path visualization objects from render only, but keep them visible in viewport.
        This allows the path to be visible when opening the .blend file but not appear in rendered images.
        """
        print("🔒 Hiding camera path visualization objects from render only...")

        # Hide all path objects from render only (keep viewport visible)
        for obj in created_objects:
            try:
                # Keep visible in viewport
                obj.hide_viewport = False
                # Hide from render only
                obj.hide_render = True
                # Keep selectable
                obj.hide_select = False
                # Keep visible for camera view in viewport
                obj.visible_camera = True
                # Hide from all render passes
                obj.visible_diffuse = False
                obj.visible_glossy = False
                obj.visible_transmission = False
                obj.visible_volume_scatter = False
                obj.visible_shadow = False
                print(f"   🔒 Hidden from render: {obj.name} (viewport: visible)")
            except Exception as e:
                print(f"   ⚠️ Error hiding object {obj.name}: {e}")

        # Hide the path collection from render only
        for collection in bpy.data.collections:
            if "CameraPath_Scene" in collection.name:
                try:
                    # Keep visible in viewport
                    collection.hide_viewport = False
                    # Hide from render only
                    collection.hide_render = True
                except Exception as e:
                    print(f"   ⚠️ Error hiding collection {collection.name}: {e}")

        # Force viewport update
        try:
            bpy.context.view_layer.update()
            print(
                "   ✅ Viewport updated - paths visible in viewport, hidden from render"
            )
        except Exception:
            pass

    def check_camera_path_visibility(self, created_objects):
        """
        Check the visibility status of camera path visualization objects.
        Useful for debugging visibility issues.
        """
        print("🔍 Checking camera path visibility status...")

        viewport_visible_count = 0
        render_visible_count = 0
        total_count = 0

        for obj in created_objects:
            try:
                viewport_visible = not obj.hide_viewport
                render_visible = not obj.hide_render

                if viewport_visible:
                    viewport_visible_count += 1
                if render_visible:
                    render_visible_count += 1
                total_count += 1
            except Exception as e:
                print(f"   ⚠️ Error checking object {obj.name}: {e}")

        # Check collection visibility
        for collection in bpy.data.collections:
            if "CameraPath_Scene" in collection.name:
                try:
                    viewport_visible = not collection.hide_viewport
                    render_visible = not collection.hide_render
                except Exception as e:
                    print(f"   ⚠️ Error checking collection {collection.name}: {e}")

        print(
            f"📊 Summary: {viewport_visible_count}/{total_count} visible in viewport, {render_visible_count}/{total_count} visible in render"
        )

    def show_camera_path_visualization(self, created_objects):
        """
        Show the camera path visualization objects and collection in both viewport and render.
        This makes the paths fully visible for debugging or when you want to see them in renders.
        """
        print("👁️ Showing camera path visualization objects in viewport and render...")

        # Show all path objects in both viewport and render
        for obj in created_objects:
            try:
                # Show in viewport
                obj.hide_viewport = False
                # Show in render
                obj.hide_render = False
                # Show for selection
                obj.hide_select = False
                # Set as visible for all render passes
                obj.visible_camera = True
                obj.visible_diffuse = True
                obj.visible_glossy = True
                obj.visible_transmission = True
                obj.visible_volume_scatter = True
                obj.visible_shadow = True
                print(
                    f"   👁️ Shown object: {obj.name} (viewport: visible, render: visible)"
                )
            except Exception as e:
                print(f"   ⚠️ Error showing object {obj.name}: {e}")

        # Show the path collection in both viewport and render
        for collection in bpy.data.collections:
            if "CameraPath_Scene" in collection.name:
                try:
                    collection.hide_viewport = False
                    collection.hide_render = False
                except Exception as e:
                    print(f"   ⚠️ Error showing collection {collection.name}: {e}")

        # Force viewport update
        try:
            bpy.context.view_layer.update()
            print("   ✅ Viewport updated - paths visible in both viewport and render")
        except Exception:
            pass

    def remove_camera_path_visualization(self, created_objects):
        """
        Remove the camera path visualization objects and collection from the scene.
        This is used for cleanup after generation is complete.
        """
        # Remove all objects first
        for obj in created_objects:
            with contextlib.suppress(Exception):
                bpy.data.objects.remove(obj, do_unlink=True)

        # Remove the path collection
        for collection in bpy.data.collections:
            if "CameraPath_Scene" in collection.name:
                with contextlib.suppress(Exception):
                    bpy.data.collections.remove(collection)

        # Also clean up materials
        for mat in bpy.data.materials:
            if (
                "PathMaterial_Scene" in mat.name
                or "MarkerMaterial_Scene" in mat.name
                or "ArrowMaterial_Scene" in mat.name
            ):
                with contextlib.suppress(Exception):
                    bpy.data.materials.remove(mat)

    def save_generated_scene_with_path(self, scene_id, camera_path):
        """
        Save the Blender scene with camera path visualization using the same batch naming.
        """
        try:
            # Use the same folder structure as the regular scene saving
            scenes_folder = Path("scenes")
            scenes_folder.mkdir(exist_ok=True)

            # Generate scene filename with batch info (same as regular scene saving)
            batch_name = os.path.basename(
                self.config.get("output_dir", "unknown_batch")
            )

            # Create a subfolder inside scenes for better organization
            scenes_warehouse_folder = scenes_folder / "warehouse_generated"
            scenes_warehouse_folder.mkdir(exist_ok=True)

            # Save the scene with the same naming as the batch
            scene_filename = (
                f"warehouse_generated_scene_{scene_id+1}_{batch_name}.blend"
            )
            scene_path = scenes_warehouse_folder / scene_filename

            # Remove existing file if it exists to prevent .blend1 backup
            if scene_path.exists():
                scene_path.unlink()

            # Disable auto-save to prevent .blend1 files
            original_auto_save = (
                bpy.context.preferences.filepaths.use_auto_save_temporary_files
            )
            bpy.context.preferences.filepaths.use_auto_save_temporary_files = False

            # Save the scene (use copy=True to avoid .blend1 backup)
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path), copy=True)
            print(f"💾 Saving generated scene to: {scene_path}")

            # Restore auto-save setting
            bpy.context.preferences.filepaths.use_auto_save_temporary_files = (
                original_auto_save
            )

            # Also save the camera path data as JSON for reference
            json_filename = (
                f"warehouse_generated_scene_{scene_id+1}_{batch_name}_camera_path.json"
            )
            json_path = scenes_warehouse_folder / json_filename

            path_data = {
                "scene_id": scene_id,
                "batch_name": batch_name,
                "path_points": len(camera_path),
                "camera_path": [
                    {
                        "position": [p["position"].x, p["position"].y, p["position"].z],
                        "rotation": [p["rotation"].x, p["rotation"].y, p["rotation"].z],
                    }
                    for p in camera_path
                ],
            }

            with open(json_path, "w") as f:
                json.dump(path_data, f, indent=2)

            print(f"✅ Scene saved successfully: {scene_filename}")
            print(f"📄 Camera path data saved: {json_filename}")

        except Exception as e:
            print(f"❌ Error saving scene with camera path: {e}")

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

        print(f"Total templates box found: {len(box_templates)}")
        if not box_templates:
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
            # Process boxes in this collection
            for box in collection_group["boxes"]:
                if (
                    box.name.lower() not in templates_to_keep
                    and random.random() < box_removal_prob
                ):
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
                        template.hide_viewport = False
                    if template.hide_render:
                        template.hide_render = False

                    # Add to collection FIRST
                    self._add_box_to_collection(box, boxes_collection)

                    # Position in world coordinates - EXACT original logic
                    box.location = world_pos

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
                obj.location.z += dz
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
        keypoints_data=None,
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
                # Use simplified legend for warehouse mode by default
                if self.config.get("warehouse_simplified_legend", True):
                    success = self.create_analysis_image_multi(
                        img_path,
                        b2d_list,
                        b3d_list,
                        pockets_list,
                        cam_obj,
                        sc,
                        ana_path,
                        frame_id,
                        keypoints_data,
                    )
                else:
                    # Use base class method with detailed legend
                    success = super().create_analysis_image_multi(
                        img_path,
                        b2d_list,
                        b3d_list,
                        pockets_list,
                        cam_obj,
                        sc,
                        ana_path,
                        frame_id,
                        keypoints_data,
                    )
                if success:
                    print(f"📊 Warehouse analysis image saved: {ana_path}")
                else:
                    print(f"⚠️ Failed to create analysis image for frame {frame_id}")
            except Exception as e:
                print(f"    ⚠️ Analysis generation error: {e}")

        # Save keypoints labels
        if keypoints_data:
            self.save_keypoints_labels(keypoints_data, frame_id, img_w, img_h)

        # Metadata
        meta.append(
            {
                "frame": frame_id,
                "image_id": img_filename[:-4],  # Remove .png
                "rgb": img_path,
                "visible_pallets": len(visible_pallets),
                "faces_detected": len(keypoints_data) if keypoints_data else 0,
                "keypoints_total": (
                    sum(len(face_data["keypoints"]) for face_data in keypoints_data)
                    if keypoints_data
                    else 0
                ),
                "keypoints_visible": (
                    sum(
                        sum(1 for kp in face_data["keypoints"] if kp["visible"])
                        for face_data in keypoints_data
                    )
                    if keypoints_data
                    else 0
                ),
                "faces": (
                    [
                        {
                            "object_name": face_data["face_object"].name,
                            "face_name": face_data["face_name"],
                            "face_index": face_data["face_index"],
                            "keypoints_count": len(face_data["keypoints"]),
                            "visible_keypoints": sum(
                                1 for kp in face_data["keypoints"] if kp["visible"]
                            ),
                            "keypoints": [
                                {
                                    "name": kp["name"],
                                    "visible": kp["visible"],
                                    "position_2d": kp["position_2d"],
                                    "position_3d": kp["position_3d"],
                                }
                                for kp in face_data["keypoints"]
                            ],
                        }
                        for face_data in keypoints_data
                    ]
                    if keypoints_data
                    else []
                ),
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

    def select_faces_with_occlusion_detection(
        self, visible_faces, cam_obj, scene_objects
    ):
        """
        Select faces for warehouse mode considering occlusion by other pallets.
        Only selects faces that are not covered by other pallets in front of them.
        """
        if not visible_faces:
            return []

        # Check if occlusion detection is enabled
        if not self.config.get("warehouse_occlusion_detection", True):
            print("⚠️ Occlusion detection disabled, using standard face selection")
            return super().select_faces_by_camera_proximity(visible_faces, cam_obj)

        # Temporary debugging: allow disabling occlusion for testing
        if self.config.get("warehouse_disable_occlusion_for_testing", False):
            print("🧪 Testing mode: occlusion detection disabled for debugging")
            return super().select_faces_by_camera_proximity(visible_faces, cam_obj)

        # Show which occlusion detection method is being used
        if self.config.get("warehouse_comprehensive_occlusion", True):
            print("🔍 Using comprehensive occlusion detection (all objects)")
        else:
            print("🔍 Using pallet-only occlusion detection")

        # Get all pallet objects for occlusion checking
        all_pallets = scene_objects.get("pallets", [])
        max_faces_per_pallet = self.config.get("warehouse_max_faces_per_pallet", 1)

        # Group faces by pallet object
        faces_by_pallet = {}
        for face in visible_faces:
            pallet_obj = face["object"]
            if pallet_obj not in faces_by_pallet:
                faces_by_pallet[pallet_obj] = []
            faces_by_pallet[pallet_obj].append(face)

        selected_faces = []
        total_faces_checked = 0
        total_faces_occluded = 0

        # For each pallet, select the best non-occluded faces
        for pallet_obj, pallet_faces in faces_by_pallet.items():
            # Calculate face scores for this pallet's faces
            face_scores = []
            for face in pallet_faces:
                face_corners = face["face_corners_3d"]

                # Calculate distance from camera to each corner
                corner_distances = []
                for corner in face_corners:
                    distance = (cam_obj.location - corner).length
                    corner_distances.append(distance)

                # Calculate face score (lower is better - closer to camera)
                nearest_distance = min(corner_distances)
                avg_distance = sum(corner_distances) / len(corner_distances)

                face_score = nearest_distance + (avg_distance - nearest_distance) * 0.3

                face_scores.append((face, face_score, nearest_distance))

            # Sort by face score (closer faces first)
            face_scores.sort(key=lambda x: x[1])

            # Select up to max_faces_per_pallet non-occluded faces
            faces_selected_for_pallet = 0
            for face, _face_score, _nearest_distance in face_scores:
                if faces_selected_for_pallet >= max_faces_per_pallet:
                    break

                # Choose occlusion detection method based on configuration
                if self.config.get("warehouse_comprehensive_occlusion", True):
                    is_occluded = self.is_face_occluded_by_any_object(
                        face, pallet_obj, cam_obj
                    )
                else:
                    is_occluded = self.is_face_occluded_by_other_pallets(
                        face, pallet_obj, all_pallets, cam_obj
                    )

                total_faces_checked += 1
                if not is_occluded:
                    selected_faces.append(face)
                    faces_selected_for_pallet += 1

                else:
                    total_faces_occluded += 1

        return selected_faces

    def is_face_occluded_by_other_pallets(
        self, face, face_pallet, all_pallets, cam_obj
    ):
        """
        Check if a face is occluded by other pallets in front of it.
        Returns True if the face is occluded, False if it's visible.
        """
        face_center = face["face_center_3d"]
        camera_pos = cam_obj.location

        # Create a ray from camera to face center
        ray_direction = (face_center - camera_pos).normalized()
        ray_length = (face_center - camera_pos).length

        # Check each other pallet for intersection with the ray
        for other_pallet in all_pallets:
            if other_pallet == face_pallet:
                continue  # Skip the same pallet

            # Get the other pallet's bounding box
            other_bbox = self.bbox_3d_oriented(other_pallet)
            other_corners = [Vector(c) for c in other_bbox["corners"]]

            # Check if the ray intersects with the other pallet's bounding box
            if self.ray_intersects_bbox(
                camera_pos, ray_direction, other_corners, ray_length
            ):
                # Additional check: make sure the intersecting pallet is actually in front
                other_center = sum(other_corners, Vector()) / len(other_corners)
                other_distance = (other_center - camera_pos).length
                face_distance = (face_center - camera_pos).length

                # Use tolerance to avoid false positives from very close distances
                tolerance = self.config.get("warehouse_occlusion_tolerance", 0.3)

                # More sophisticated occlusion check:
                # 1. The other pallet must be closer to camera than the face
                # 2. The other pallet must be significantly closer (using tolerance)
                # 3. The other pallet must actually be in the line of sight
                if other_distance < (face_distance - tolerance):
                    # Additional check: make sure the other pallet is actually blocking the view
                    # by checking if the face center is behind the other pallet's center
                    face_to_other = (other_center - face_center).normalized()
                    camera_to_face = (face_center - camera_pos).normalized()

                    # If the dot product is positive, the other pallet is between camera and face
                    if face_to_other.dot(camera_to_face) > 0:
                        return True

        return False

    def ray_intersects_bbox(
        self, ray_origin, ray_direction, bbox_corners, max_distance
    ):
        """
        Check if a ray intersects with a 3D bounding box.
        Uses the slab method for ray-box intersection.
        """
        # Calculate bounding box min/max
        min_x = min(corner.x for corner in bbox_corners)
        max_x = max(corner.x for corner in bbox_corners)
        min_y = min(corner.y for corner in bbox_corners)
        max_y = max(corner.y for corner in bbox_corners)
        min_z = min(corner.z for corner in bbox_corners)
        max_z = max(corner.z for corner in bbox_corners)

        # Ray-box intersection using slab method
        t_min = 0.0
        t_max = max_distance

        # Check X axis
        if abs(ray_direction.x) < 1e-6:
            if ray_origin.x < min_x or ray_origin.x > max_x:
                return False
        else:
            t1 = (min_x - ray_origin.x) / ray_direction.x
            t2 = (max_x - ray_origin.x) / ray_direction.x
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
            if t_min > t_max:
                return False

        # Check Y axis
        if abs(ray_direction.y) < 1e-6:
            if ray_origin.y < min_y or ray_origin.y > max_y:
                return False
        else:
            t1 = (min_y - ray_origin.y) / ray_direction.y
            t2 = (max_y - ray_origin.y) / ray_direction.y
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
            if t_min > t_max:
                return False

        # Check Z axis
        if abs(ray_direction.z) < 1e-6:
            if ray_origin.z < min_z or ray_origin.z > max_z:
                return False
        else:
            t1 = (min_z - ray_origin.z) / ray_direction.z
            t2 = (max_z - ray_origin.z) / ray_direction.z
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)
            if t_min > t_max:
                return False

        return t_min <= t_max and t_min >= 0

    def get_all_scene_objects_for_occlusion(self):
        """
        Get all mesh objects in the scene that could potentially occlude pallet faces.
        This includes pallets, boxes, and any other mesh objects.
        """
        all_objects = []

        for obj in bpy.context.scene.objects:
            if obj.type == "MESH" and obj.visible_get():
                # Skip very small objects that are unlikely to cause occlusion
                if hasattr(obj, "dimensions"):
                    min_dimension = min(
                        obj.dimensions.x, obj.dimensions.y, obj.dimensions.z
                    )
                    min_size = self.config.get("warehouse_min_object_size", 0.01)
                    if min_dimension < min_size:
                        continue

                all_objects.append(obj)

        return all_objects

    def is_face_occluded_by_any_object(self, face, face_pallet, cam_obj):
        """
        Check if a face is occluded by any object in the scene (not just other pallets).
        This is a more comprehensive occlusion detection that considers all mesh objects.
        Uses multiple sample points on the face for more accurate occlusion detection.
        """
        face_corners = face["face_corners_3d"]
        camera_pos = cam_obj.location

        # Get all objects that could potentially occlude
        all_objects = self.get_all_scene_objects_for_occlusion()
        debug_occlusion = self.config.get("warehouse_debug_occlusion", False)
        tolerance = self.config.get("warehouse_occlusion_tolerance", 0.1)

        if debug_occlusion:
            print(
                f"   🔍 Checking {len(all_objects)} objects for occlusion of face {face['face_name']}"
            )

        # Check multiple points on the face for more accurate occlusion detection
        # Sample points: center + all corners
        sample_points = [face["face_center_3d"]] + face_corners

        # Add some intermediate points for better coverage
        for i in range(len(face_corners)):
            next_i = (i + 1) % len(face_corners)
            mid_point = (face_corners[i] + face_corners[next_i]) / 2
            sample_points.append(mid_point)

        # Check each object for intersection with rays to face sample points
        for obj in all_objects:
            if obj == face_pallet:
                continue  # Skip the same pallet

            # Get the object's bounding box
            try:
                bbox_3d = self.bbox_3d_oriented(obj)
                obj_corners = [Vector(c) for c in bbox_3d["corners"]]
            except Exception:
                # Fallback to simple bounding box if oriented bbox fails
                try:
                    obj_corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
                except Exception:
                    continue  # Skip this object if we can't get its bounds

            # Check if any ray from camera to face sample points intersects with this object
            occluded_points = 0
            total_points = len(sample_points)

            for sample_point in sample_points:
                ray_direction = (sample_point - camera_pos).normalized()
                ray_length = (sample_point - camera_pos).length

                # Check if the ray intersects with the object's bounding box
                if self.ray_intersects_bbox(
                    camera_pos, ray_direction, obj_corners, ray_length
                ):
                    # Additional check: make sure the intersecting object is actually in front
                    obj_center = sum(obj_corners, Vector()) / len(obj_corners)
                    obj_distance = (obj_center - camera_pos).length
                    face_distance = (sample_point - camera_pos).length

                    if obj_distance < (face_distance - tolerance):
                        # Additional check: make sure the object is actually blocking the view
                        face_to_obj = (obj_center - sample_point).normalized()
                        camera_to_face = (sample_point - camera_pos).normalized()

                        # If the dot product is positive, the object is between camera and face
                        if face_to_obj.dot(camera_to_face) > 0:
                            occluded_points += 1

            # If more than 50% of the face sample points are occluded, consider the face occluded
            occlusion_ratio = occluded_points / total_points
            if occlusion_ratio > 0.5:
                if debug_occlusion:
                    print(
                        f"   🚫 Face {face['face_name']} occluded by {obj.name} ({occluded_points}/{total_points} points occluded, ratio: {occlusion_ratio:.2f})"
                    )
                return True
            elif debug_occlusion and occluded_points > 0:
                print(
                    f"   ⚠️ Face {face['face_name']} partially occluded by {obj.name} ({occluded_points}/{total_points} points, ratio: {occlusion_ratio:.2f})"
                )

        return False

    def create_consolidated_3d_debug_visualization(
        self, visible_pallets, cam_obj, frame_id, keypoints_data
    ):
        """
        Create a consolidated 3D visualization showing all visible pallets, camera position, and selected faces.
        This replaces individual pallet debug visualizations with a single comprehensive view.
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError as e:
            print(f"Matplotlib not available for 3D visualization: {e}")
            return

        if not visible_pallets:
            print("No visible pallets to visualize")
            return

        # Get camera position
        camera_pos = cam_obj.location

        # Create figure with larger size for multiple pallets
        fig = plt.figure(figsize=(20, 15))
        ax = fig.add_subplot(111, projection="3d")

        # Colors for different pallets
        pallet_colors = [
            "red",
            "blue",
            "green",
            "orange",
            "purple",
            "brown",
            "pink",
            "gray",
            "olive",
            "cyan",
        ]

        all_corners = []
        all_pallet_info = []

        # Process each visible pallet - only show pallets with selected faces
        pallets_with_selected_faces = []
        for pallet_idx, pallet_info in enumerate(visible_pallets):
            pallet_obj = pallet_info["pallet"]

            # Get selected faces for this pallet
            pallet_selected_faces = []
            for face_data in keypoints_data:
                if face_data["face_object"] == pallet_obj:
                    pallet_selected_faces.append(face_data)

            # Only process pallets that have selected faces
            if pallet_selected_faces:
                pallets_with_selected_faces.append(
                    (pallet_idx, pallet_info, pallet_selected_faces)
                )

        # Process only pallets with selected faces
        for (
            pallet_idx,
            pallet_info,
            pallet_selected_faces,
        ) in pallets_with_selected_faces:
            pallet_obj = pallet_info["pallet"]
            color = pallet_colors[pallet_idx % len(pallet_colors)]

            # Get pallet bounding box and corners
            bbox_3d = self.bbox_3d_oriented(pallet_obj)
            corners_3d = [Vector(c) for c in bbox_3d["corners"]]
            all_corners.extend(corners_3d)

            # Plot pallet corners (simplified - no labels)
            corner_x = [corner.x for corner in corners_3d]
            corner_y = [corner.y for corner in corners_3d]
            corner_z = [corner.z for corner in corners_3d]

            # Plot corners as colored dots (smaller size, no labels)
            ax.scatter(
                corner_x,
                corner_y,
                corner_z,
                c=color,
                s=40,  # Smaller size for cleaner look
                alpha=0.8,
                label=(
                    f"Pallets: {len(pallets_with_selected_faces)}"
                    if pallet_idx == pallets_with_selected_faces[0][0]
                    else None
                ),  # Only show legend for first pallet
            )

            # Draw lines connecting corners to show the pallet structure (simplified)
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
                    [start.x, end.x],
                    [start.y, end.y],
                    [start.z, end.z],
                    color=color,
                    alpha=0.3,  # More transparent for cleaner look
                    linewidth=0.8,  # Thinner lines
                )

            # Plot only selected faces (no labels, simplified)
            for face_data in pallet_selected_faces:
                face_corners_3d = face_data.get("face_corners_3d", [])
                if len(face_corners_3d) >= 4:
                    face_center = sum(face_corners_3d, Vector()) / len(face_corners_3d)

                    # Only show selected faces as lime diamonds
                    ax.scatter(
                        [face_center.x],
                        [face_center.y],
                        [face_center.z],
                        c="lime",
                        s=80,  # Smaller size
                        alpha=0.9,
                        marker="D",  # Diamond marker
                        label=(
                            "Selected Faces"
                            if pallet_idx == pallets_with_selected_faces[0][0]
                            else None
                        ),
                    )

            # Store pallet info for coordinate file
            all_pallet_info.append(
                {
                    "pallet": pallet_obj,
                    "corners": corners_3d,
                    "selected_faces": pallet_selected_faces,
                    "color": color,
                }
            )

        # Plot camera position (simplified - no text label)
        ax.scatter(
            [camera_pos.x],
            [camera_pos.y],
            [camera_pos.z],
            c="black",
            s=200,  # Smaller size
            label="Camera",
            marker="^",
        )

        # Removed distance lines and labels for cleaner visualization

        # Set labels and title
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_zlabel("Z")

        # Calculate statistics for the title (only pallets with selected faces)
        num_pallets = len(pallets_with_selected_faces)
        num_faces = len(keypoints_data) if keypoints_data else 0
        total_keypoints = (
            sum(len(face.get("keypoints", [])) for face in keypoints_data)
            if keypoints_data
            else 0
        )
        visible_keypoints = (
            sum(
                sum(1 for kp in face.get("keypoints", []) if kp.get("visible", False))
                for face in keypoints_data
            )
            if keypoints_data
            else 0
        )

        ax.set_title(
            f"Warehouse Frame {frame_id} - 3D Debug View\n"
            f"Pallets: {num_pallets} | Faces: {num_faces} | Keypoints: {visible_keypoints}/{total_keypoints}"
        )

        # Add legend
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

        # Set equal aspect ratio for all pallets
        if all_corners:
            all_x = [corner.x for corner in all_corners] + [camera_pos.x]
            all_y = [corner.y for corner in all_corners] + [camera_pos.y]
            all_z = [corner.z for corner in all_corners] + [camera_pos.z]

            max_range = max(
                max(all_x) - min(all_x),
                max(all_y) - min(all_y),
                max(all_z) - min(all_z),
            )
            mid_x = (max(all_x) + min(all_x)) * 0.5
            mid_y = (max(all_y) + min(all_y)) * 0.5
            mid_z = (max(all_z) + min(all_z)) * 0.5

            ax.set_xlim(mid_x - max_range / 2, mid_x + max_range / 2)
            ax.set_ylim(mid_y - max_range / 2, mid_y + max_range / 2)
            ax.set_zlim(mid_z - max_range / 2, mid_z + max_range / 2)

        # Save the consolidated plot as PNG image
        output_path = os.path.join(
            self.paths["debug_3d_images"],
            f"frame_{frame_id:06d}_warehouse_3d_debug.png",
        )

        try:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            print(f"✅ Consolidated 3D debug visualization saved to: {output_path}")
        except Exception as e:
            print(f"❌ Error saving consolidated 3D plot: {e}")
            plt.close()
            return

        plt.close()

        # Create interactive HTML visualization
        self.create_consolidated_interactive_3d_html(
            visible_pallets, cam_obj, frame_id, keypoints_data
        )

        # Save consolidated coordinate data as text file
        coord_file = os.path.join(
            self.paths["debug_3d_coordinates"],
            f"frame_{frame_id:06d}_warehouse_coordinates.txt",
        )

        try:
            with open(coord_file, "w") as f:
                f.write(
                    f"Warehouse Frame {frame_id} - Consolidated 3D Coordinates Debug\n"
                )
                f.write(
                    f"Camera Position: ({camera_pos.x:.3f}, {camera_pos.y:.3f}, {camera_pos.z:.3f})\n"
                )
                f.write(f"Total Visible Pallets: {len(visible_pallets)}\n")
                f.write(f"Total Selected Faces: {len(keypoints_data)}\n\n")

                # Write data for each pallet
                for pallet_idx, pallet_info in enumerate(all_pallet_info):
                    pallet_obj = pallet_info["pallet"]
                    corners_3d = pallet_info["corners"]
                    selected_faces = pallet_info["selected_faces"]

                    f.write(f"=== PALLET {pallet_idx}: {pallet_obj.name} ===\n")
                    f.write(f"Color: {pallet_info['color']}\n")

                    # Calculate pallet center and distance
                    pallet_center = sum(corners_3d, Vector()) / len(corners_3d)
                    distance = (camera_pos - pallet_center).length
                    f.write(
                        f"Center: ({pallet_center.x:.3f}, {pallet_center.y:.3f}, {pallet_center.z:.3f})\n"
                    )
                    f.write(f"Distance from camera: {distance:.3f}m\n")

                    # Write corner coordinates
                    f.write("Corner Points (8 corners):\n")
                    for i, corner in enumerate(corners_3d):
                        corner_distance = (camera_pos - corner).length
                        f.write(
                            f"  Corner {i}: ({corner.x:.3f}, {corner.y:.3f}, {corner.z:.3f}) - Distance: {corner_distance:.3f}m\n"
                        )

                    # Write selected faces
                    if selected_faces:
                        f.write("Selected Faces:\n")
                        for face_data in selected_faces:
                            f.write(
                                f"  - {face_data['face_name']}: {len(face_data['keypoints'])} keypoints\n"
                            )
                    else:
                        f.write("Selected Faces: None\n")

                    f.write("\n")

                # Write summary of all selected faces
                f.write("=== SUMMARY OF ALL SELECTED FACES ===\n")
                for i, face_data in enumerate(keypoints_data):
                    pallet_name = face_data["face_object"].name
                    visible_kp = sum(
                        1 for kp in face_data["keypoints"] if kp["visible"]
                    )
                    total_kp = len(face_data["keypoints"])
                    f.write(
                        f"{i+1}. {pallet_name} - {face_data['face_name']}: {visible_kp}/{total_kp} keypoints visible\n"
                    )

            print(f"✅ Consolidated coordinate data saved to: {coord_file}")

        except Exception as e:
            print(f"❌ Error saving consolidated coordinate data: {e}")

    def generate_keypoints_for_frame(self, cam_obj, sc, frame_id=None):
        """
        Override the base class method to use consolidated debug visualization for warehouse mode.
        This creates a single debug visualization showing all visible pallets instead of individual ones.
        """
        # Detect faces in the scene using our occlusion-aware method
        faces = self.detect_faces_in_scene(cam_obj, sc)

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

        # Create consolidated 3D debug visualization for warehouse mode
        if frame_id is not None:
            # Get visible pallets for consolidated visualization
            scene_objects = self.find_warehouse_objects()
            visible_pallets = self.get_visible_pallets(scene_objects, cam_obj, sc)

            if visible_pallets:
                print(
                    f"🎯 Creating consolidated 3D debug visualization for {len(visible_pallets)} pallets"
                )
                self.create_consolidated_3d_debug_visualization(
                    visible_pallets, cam_obj, frame_id, keypoints_data
                )
            else:
                print(
                    "⚠️ No visible pallets found for consolidated debug visualization"
                )

            # Generate 2D boxes and 3D coordinates for selected faces (same as base class)
            img_width = self.config.get("resolution_x", 1280)
            img_height = self.config.get("resolution_y", 720)
            self.generate_face_2d_boxes(faces, frame_id, img_width, img_height)
            self.generate_face_3d_coordinates(faces, frame_id, img_width, img_height)

        return keypoints_data

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
        Override the base class method to create a simplified legend for warehouse mode.
        Shows only statistics instead of individual face details to avoid overcrowding.
        """
        import os

        from PIL import Image, ImageDraw, ImageFont

        # Load the RGB image
        try:
            img = Image.open(rgb_path)
        except Exception as e:
            print(f"❌ Error loading image {rgb_path}: {e}")
            return False

        # Create a drawing context
        draw = ImageDraw.Draw(img)

        # Try to load a font, fallback to default if not available
        try:
            font = ImageFont.truetype(
                "arial.ttf", 14
            )  # Larger font for better visibility
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        # Colors for different elements
        color_2d = (255, 0, 0)  # Red for 2D bboxes
        color_3d = (0, 255, 0)  # Green for 3D bboxes
        color_hole = (0, 0, 255)  # Blue for holes
        face_colors = [
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 165, 0),  # Orange
            (128, 0, 128),  # Purple
            (255, 192, 203),  # Pink
        ]

        # Draw 2D bounding boxes with labels
        if bboxes2d and self.config.get("analysis_show_all_labels", True):
            for i, bbox in enumerate(bboxes2d):
                if bbox and len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox[:4]
                    draw.rectangle([x1, y1, x2, y2], outline=color_2d, width=2)
                    # Add label for 2D bbox with background
                    label_text = f"2D-{i+1}"
                    label_x, label_y = x1, y1 - 25

                    # Draw background for better visibility
                    if font:
                        bbox = draw.textbbox((label_x, label_y), label_text, font=font)
                        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    else:
                        text_w, text_h = len(label_text) * 8, 12

                    draw.rectangle(
                        [
                            label_x - 2,
                            label_y - 2,
                            label_x + text_w + 2,
                            label_y + text_h + 2,
                        ],
                        fill=(0, 0, 0, 180),
                        outline=color_2d,
                        width=1,
                    )
                    draw.text(
                        (label_x, label_y), label_text, fill=(255, 255, 255), font=font
                    )

        # Draw 3D bounding boxes with labels
        if bboxes3d and self.config.get("analysis_show_all_labels", True):
            for i, bbox_3d in enumerate(bboxes3d):
                if bbox_3d and len(bbox_3d) >= 8:
                    # Convert 3D corners to 2D
                    corners_2d = []
                    for corner_3d in bbox_3d:
                        if len(corner_3d) >= 3:
                            # Project 3D point to 2D using camera
                            world_coord = Vector(corner_3d[:3])
                            co_2d = bpy_extras.object_utils.world_to_camera_view(
                                sc, cam_obj, world_coord
                            )
                            if co_2d:
                                x, y, z = co_2d
                                corners_2d.append((x, y))

                    # Draw 3D bbox edges
                    if len(corners_2d) >= 8:
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
                            if edge[0] < len(corners_2d) and edge[1] < len(corners_2d):
                                start = corners_2d[edge[0]]
                                end = corners_2d[edge[1]]
                                draw.line([start, end], fill=color_3d, width=2)

                        # Add corner numbers and 3D bbox label
                        for j, corner in enumerate(corners_2d[:8]):
                            corner_text = str(j + 1)
                            corner_x, corner_y = corner[0] + 8, corner[1] - 8

                            # Draw background for corner numbers
                            if font:
                                bbox = draw.textbbox(
                                    (corner_x, corner_y), corner_text, font=font
                                )
                                text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                            else:
                                text_w, text_h = len(corner_text) * 8, 12

                            draw.rectangle(
                                [
                                    corner_x - 2,
                                    corner_y - 2,
                                    corner_x + text_w + 2,
                                    corner_y + text_h + 2,
                                ],
                                fill=(0, 0, 0, 180),
                                outline=color_3d,
                                width=1,
                            )
                            draw.text(
                                (corner_x, corner_y),
                                corner_text,
                                fill=(255, 255, 255),
                                font=font,
                            )

                        # Add 3D bbox label at the center
                        center_x = sum(corner[0] for corner in corners_2d[:8]) / 8
                        center_y = sum(corner[1] for corner in corners_2d[:8]) / 8
                        label_text = f"3D-{i+1}"

                        # Draw background for center label
                        if font:
                            bbox = draw.textbbox(
                                (center_x, center_y), label_text, font=font
                            )
                            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        else:
                            text_w, text_h = len(label_text) * 8, 12

                        draw.rectangle(
                            [
                                center_x - 2,
                                center_y - 2,
                                center_x + text_w + 2,
                                center_y + text_h + 2,
                            ],
                            fill=(0, 0, 0, 180),
                            outline=color_3d,
                            width=1,
                        )
                        draw.text(
                            (center_x, center_y),
                            label_text,
                            fill=(255, 255, 255),
                            font=font,
                        )

        # Draw holes/pockets with labels
        if all_pockets_world and self.config.get("analysis_show_all_labels", True):
            hole_count = 0
            for pockets in all_pockets_world:
                for pocket in pockets:
                    if pocket and len(pocket) >= 4:
                        x1, y1, x2, y2 = pocket[:4]
                        draw.rectangle([x1, y1, x2, y2], outline=color_hole, width=2)
                        # Add hole label
                        hole_count += 1
                        label_text = f"H-{hole_count}"
                        draw.text((x1, y1 - 15), label_text, fill=color_hole, font=font)

        # Draw keypoints and faces with labels
        if keypoints_data and self.config.get("analysis_show_keypoints", True):
            for face_idx, face_data in enumerate(keypoints_data):
                face_color = face_colors[face_idx % len(face_colors)]
                keypoints = face_data.get("keypoints", [])
                face_corners_3d = face_data.get("face_corners_3d", [])
                face_name = face_data.get("face_name", f"face_{face_idx}")

                # Draw keypoints with labels
                for kp_idx, kp in enumerate(keypoints):
                    visible = kp.get("visible", False)
                    # Get 2D coordinates from position_2d field
                    position_2d = kp.get("position_2d", [0, 0])
                    x, y = position_2d[0], position_2d[1]
                    if visible:
                        draw.ellipse(
                            [x - 4, y - 4, x + 4, y + 4],
                            fill=face_color,
                            outline=(0, 0, 0),
                            width=1,
                        )
                        # Add keypoint number with background for better visibility
                        kp_text = str(kp_idx + 1)
                        text_x, text_y = x + 8, y - 8

                        # Draw background rectangle for text
                        if font:
                            bbox = draw.textbbox((text_x, text_y), kp_text, font=font)
                            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        else:
                            text_w, text_h = len(kp_text) * 8, 12

                        # Draw background
                        draw.rectangle(
                            [
                                text_x - 2,
                                text_y - 2,
                                text_x + text_w + 2,
                                text_y + text_h + 2,
                            ],
                            fill=(0, 0, 0, 180),  # Semi-transparent black background
                            outline=face_color,
                            width=1,
                        )

                        # Draw text
                        draw.text(
                            (text_x, text_y), kp_text, fill=(255, 255, 255), font=font
                        )

                # Draw face outline with label
                if face_corners_3d and len(face_corners_3d) >= 4:
                    corners_2d = []
                    for corner_3d in face_corners_3d:
                        world_coord = Vector(corner_3d[:3])
                        co_2d = bpy_extras.object_utils.world_to_camera_view(
                            sc, cam_obj, world_coord
                        )
                        if co_2d:
                            x, y, z = co_2d
                            corners_2d.append((x, y))

                    # Draw the face as a polygon (4 corners)
                    if len(corners_2d) == 4:
                        # Draw the face outline
                        draw.polygon(corners_2d, outline=face_color, width=3)

                        # Draw corner points for reference
                        for corner_idx, (x, y) in enumerate(corners_2d):
                            draw.ellipse(
                                [x - 3, y - 3, x + 3, y + 3],
                                fill=face_color,
                                outline=(0, 0, 0),
                                width=1,
                            )
                            # Add corner letter (A, B, C, D)
                            corner_letter = chr(65 + corner_idx)  # A, B, C, D
                            draw.text(
                                (x + 6, y + 6),
                                corner_letter,
                                fill=face_color,
                                font=font,
                            )

                        # Add face name label at the center
                        center_x = sum(corner[0] for corner in corners_2d) / 4
                        center_y = sum(corner[1] for corner in corners_2d) / 4
                        draw.text(
                            (center_x, center_y), face_name, fill=face_color, font=font
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
        if self.config.get("analysis_show_3d_coordinates", False) and keypoints_data:
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

        # Create simplified legend with statistics only
        self._draw_simplified_warehouse_legend(
            draw,
            frame_id,
            bboxes2d,
            bboxes3d,
            all_pockets_world,
            keypoints_data,
            font,
            img.width,
            img.height,
        )

        # Save the analysis image
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path)
            return True
        except Exception as e:
            print(f"❌ Error saving analysis image {output_path}: {e}")
            return False

    def create_consolidated_interactive_3d_html(
        self, visible_pallets, cam_obj, frame_id, keypoints_data
    ):
        """
        Create an interactive HTML 3D visualization for warehouse mode showing all pallets and faces.
        """
        try:
            import plotly.graph_objects as go
            import plotly.offline as pyo
        except ImportError:
            print("⚠️ Plotly not available for interactive 3D HTML generation")
            return

        if not visible_pallets:
            print("No visible pallets for HTML visualization")
            return

        # Create figure
        fig = go.Figure()

        # Colors for different pallets
        pallet_colors = [
            "red",
            "blue",
            "green",
            "orange",
            "purple",
            "brown",
            "pink",
            "gray",
            "olive",
            "cyan",
        ]

        camera_pos = cam_obj.location
        all_corners = []

        # Process each visible pallet
        for pallet_idx, pallet_info in enumerate(visible_pallets):
            pallet_obj = pallet_info["pallet"]
            color = pallet_colors[pallet_idx % len(pallet_colors)]

            # Get pallet bounding box and corners
            bbox_3d = self.bbox_3d_oriented(pallet_obj)
            corners_3d = [Vector(c) for c in bbox_3d["corners"]]
            all_corners.extend(corners_3d)

            # Add pallet corners
            corner_x = [corner.x for corner in corners_3d]
            corner_y = [corner.y for corner in corners_3d]
            corner_z = [corner.z for corner in corners_3d]

            fig.add_trace(
                go.Scatter3d(
                    x=corner_x,
                    y=corner_y,
                    z=corner_z,
                    mode="markers",  # Removed text for faster rendering
                    marker={
                        "size": 4,
                        "color": color,
                        "symbol": "circle",
                    },  # Smaller size
                    name=(
                        f"Pallets: {len(visible_pallets)}" if pallet_idx == 0 else None
                    ),  # Only show legend for first pallet
                    showlegend=pallet_idx == 0,  # Only show legend for first pallet
                    hovertemplate=f"<b>{pallet_obj.name}</b><br>"
                    "X: %{x:.2f}<br>"
                    "Y: %{y:.2f}<br>"
                    "Z: %{z:.2f}<extra></extra>",
                )
            )

            # Add pallet edges
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
                fig.add_trace(
                    go.Scatter3d(
                        x=[start.x, end.x],
                        y=[start.y, end.y],
                        z=[start.z, end.z],
                        mode="lines",
                        line={
                            "color": color,
                            "width": 1,
                        },  # Thinner lines for faster rendering
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

            # Add selected faces for this pallet
            pallet_selected_faces = []
            for face_data in keypoints_data:
                if face_data["face_object"] == pallet_obj:
                    pallet_selected_faces.append(face_data)

            # Add face centers
            all_faces = self.get_all_faces_from_bbox()

            for i, face in enumerate(all_faces):
                face_corners = [corners_3d[j] for j in face["corners"]]
                face_center = sum(face_corners, Vector()) / 4

                # Check if this face is selected
                is_selected = any(
                    f["face_name"] == face["name"] for f in pallet_selected_faces
                )

                if is_selected:
                    # Selected face - bright color, larger size
                    pass
                elif face["name"] in ["top", "bottom"]:
                    # Top/bottom faces - different marker
                    pass
                else:
                    # Side faces
                    pass

                # Only show selected faces to reduce data
                if is_selected:
                    fig.add_trace(
                        go.Scatter3d(
                            x=[face_center.x],
                            y=[face_center.y],
                            z=[face_center.z],
                            mode="markers",  # Removed text for faster rendering
                            marker={
                                "size": 8,
                                "color": "lime",
                                "symbol": "diamond",
                            },  # Simplified
                            name=(
                                "Selected Faces" if pallet_idx == 0 and i == 0 else None
                            ),  # Only show legend for first face
                            showlegend=pallet_idx == 0
                            and i == 0,  # Only show legend for first face
                            hovertemplate=f"<b>{pallet_obj.name} - {face['name']}</b><br>"
                            "X: %{x:.2f}<br>"
                            "Y: %{y:.2f}<br>"
                            "Z: %{z:.2f}<br>"
                            "Status: Selected<extra></extra>",
                        )
                    )

        # Add camera position (simplified)
        fig.add_trace(
            go.Scatter3d(
                x=[camera_pos.x],
                y=[camera_pos.y],
                z=[camera_pos.z],
                mode="markers",  # Removed text for faster rendering
                marker={
                    "size": 10,
                    "color": "black",
                    "symbol": "diamond",
                },  # Smaller size
                name="Camera",
                hovertemplate="<b>Camera</b><br>"
                "X: %{x:.2f}<br>"
                "Y: %{y:.2f}<br>"
                "Z: %{z:.2f}<extra></extra>",
            )
        )

        # Removed distance lines to reduce data and improve performance

        # Calculate statistics for the title and legend
        num_pallets = len(visible_pallets)
        num_faces = len(keypoints_data) if keypoints_data else 0
        total_keypoints = (
            sum(len(face.get("keypoints", [])) for face in keypoints_data)
            if keypoints_data
            else 0
        )
        visible_keypoints = (
            sum(
                sum(1 for kp in face.get("keypoints", []) if kp.get("visible", False))
                for face in keypoints_data
            )
            if keypoints_data
            else 0
        )

        # Set layout (optimized for performance)
        fig.update_layout(
            title=f"Warehouse Frame {frame_id} - Interactive 3D Debug View<br>"
            f"<sub>Pallets: {num_pallets} | Faces: {num_faces} | Keypoints: {visible_keypoints}/{total_keypoints}</sub>",
            scene={
                "xaxis_title": "X",
                "yaxis_title": "Y",
                "zaxis_title": "Z",
                "aspectmode": "data",
            },
            width=1000,  # Reduced size for faster loading
            height=700,  # Reduced size for faster loading
            showlegend=True,
            legend={
                "x": 1.02,
                "y": 1,
                "bgcolor": "rgba(255,255,255,0.8)",
                "bordercolor": "black",
                "borderwidth": 1,
                "title": {
                    "text": f"<b>Scene Summary</b><br>Pallets: {num_pallets}<br>Faces: {num_faces}<br>Keypoints: {visible_keypoints}/{total_keypoints}",
                    "font": {"size": 10},  # Smaller font for faster rendering
                },
            },
        )

        # Create figures folder inside debug_3d
        figures_folder = os.path.join(self.paths["debug_3d"], "figures")
        os.makedirs(figures_folder, exist_ok=True)

        # Save HTML file in figures folder
        html_path = os.path.join(
            figures_folder,
            f"frame_{frame_id:06d}_warehouse_3d_interactive.html",
        )

        try:
            # Use optimized plot settings for faster generation and loading
            pyo.plot(
                fig,
                filename=html_path,
                auto_open=False,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": [
                        "pan2d",
                        "lasso2d",
                        "select2d",
                        "autoScale2d",
                    ],
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": f"warehouse_frame_{frame_id}",
                        "height": 700,
                        "width": 1000,
                        "scale": 1,
                    },
                },
            )
            print(f"✅ Interactive 3D HTML saved to: {html_path}")
        except Exception as e:
            print(f"❌ Error saving interactive HTML: {e}")

    def _draw_simplified_warehouse_legend(
        self,
        draw,
        frame_id,
        bboxes2d,
        bboxes3d,
        all_pockets_world,
        keypoints_data,
        font,
        img_width,
        _img_height,
    ):
        """
        Draw a simplified legend showing only statistics for warehouse mode.
        """
        # Calculate statistics
        num_pallets = len(bboxes2d) if bboxes2d else 0
        num_faces = len(keypoints_data) if keypoints_data else 0
        total_keypoints = (
            sum(len(face.get("keypoints", [])) for face in keypoints_data)
            if keypoints_data
            else 0
        )
        visible_keypoints = (
            sum(
                sum(1 for kp in face.get("keypoints", []) if kp.get("visible", False))
                for face in keypoints_data
            )
            if keypoints_data
            else 0
        )
        num_holes = (
            sum(len(pockets) for pockets in all_pockets_world)
            if all_pockets_world
            else 0
        )

        # Create legend items with statistics
        legend_items = [
            f"Frame {frame_id}",
            f"Pallets: {num_pallets}",
            f"Faces: {num_faces}",
            f"Keypoints: {visible_keypoints}/{total_keypoints}",
        ]

        if num_holes > 0:
            legend_items.append(f"Holes: {num_holes}")

        # Add color indicators for what's shown
        if bboxes2d:
            legend_items.append("2D bbox")
        if bboxes3d:
            legend_items.append("3D bbox")
        if keypoints_data:
            legend_items.append("Keypoints")
        if self.config.get("analysis_show_2d_boxes", False) and keypoints_data:
            legend_items.append("2D Face Boxes")
        if self.config.get("analysis_show_3d_coordinates", False) and keypoints_data:
            legend_items.append("3D Face Coords")

        # Calculate legend dimensions
        pad = 8
        line_gap = 4
        max_width = 0
        total_height = 0

        # Get text dimensions
        text_dims = []
        for item in legend_items:
            if font:
                bbox = draw.textbbox((0, 0), item, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            else:
                w, h = len(item) * 6, 12  # Approximate dimensions
            text_dims.append((w, h))
            max_width = max(max_width, w)
            total_height += h

        # Add padding and gaps
        legend_w = max_width + 2 * pad
        legend_h = total_height + (len(legend_items) - 1) * line_gap + 2 * pad

        # Position legend in top-right corner
        lx = img_width - legend_w - 10
        ly = 10

        # Draw legend background
        draw.rectangle([lx, ly, lx + legend_w, ly + legend_h], fill=(0, 0, 0, 180))

        # Draw legend text
        y = ly + pad
        for _i, (item, (_w, h)) in enumerate(
            zip(legend_items, text_dims, strict=False)
        ):
            # Add color indicators for certain items
            color = (255, 255, 255)  # White text
            if item == "2D bbox":
                color = (255, 0, 0)  # Red
            elif item == "3D bbox":
                color = (0, 255, 0)  # Green
            elif item == "Keypoints":
                color = (255, 255, 0)  # Yellow
            elif item == "2D Face Boxes":
                color = (255, 0, 255)  # Magenta
            elif item == "3D Face Coords":
                color = (0, 255, 255)  # Cyan

            draw.text((lx + pad, y), item, fill=color, font=font)
            y += h + line_gap

    def detect_faces_in_scene(self, cam_obj, sc):
        """
        Override the base class method to use occlusion-aware face selection for warehouse mode.
        This ensures only non-occluded faces are selected.
        """
        # First, get all visible faces using the base class method
        all_visible_faces = super().detect_faces_in_scene(cam_obj, sc)

        if not all_visible_faces:
            print("🎯 No visible faces detected in scene")
            return []

        print(f"🎯 Detected {len(all_visible_faces)} visible faces in scene")

        # Get scene objects for occlusion checking
        scene_objects = self.find_warehouse_objects()

        # Use our occlusion-aware face selection
        selected_faces = self.select_faces_with_occlusion_detection(
            all_visible_faces, cam_obj, scene_objects
        )

        return selected_faces

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
            # Remove existing file if it exists to prevent .blend1 backup
            if scene_path.exists():
                scene_path.unlink()

            # Disable auto-save to prevent .blend1 files
            original_auto_save = (
                bpy.context.preferences.filepaths.use_auto_save_temporary_files
            )
            bpy.context.preferences.filepaths.use_auto_save_temporary_files = False

            print(f"💾 Saving generated scene to: {scene_path}")
            import sys

            sys.stdout.flush()
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path), copy=True)
            print(f"✅ Scene saved successfully: {scene_filename}")
            sys.stdout.flush()

            # Restore auto-save setting
            bpy.context.preferences.filepaths.use_auto_save_temporary_files = (
                original_auto_save
            )

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
