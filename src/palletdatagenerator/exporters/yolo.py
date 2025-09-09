"""YOLO format exporter for object detection annotations."""

import json
from pathlib import Path
from typing import Any

try:
    import bpy
    from bpy_extras.object_utils import world_to_camera_view as w2cv
    from mathutils import Vector

    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False


class YOLOExporter:
    """Export object detection annotations in YOLO format.

    YOLO format specifications:
    - One text file per image
    - Each line: class_id center_x center_y width height
    - All coordinates normalized to [0, 1]
    """

    def __init__(self, output_dir: str, class_mapping: dict[str, int] | None = None):
        """Initialize YOLO exporter.

        Args:
            output_dir: Directory to save YOLO label files
            class_mapping: Dictionary mapping class names to class IDs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.class_mapping = class_mapping or {"pallet": 0, "box": 1, "hole": 2}

        # Create classes.txt file
        self._create_classes_file()

    def _create_classes_file(self) -> None:
        """Create classes.txt file with class names."""
        classes_file = self.output_dir / "classes.txt"

        # Sort classes by ID
        sorted_classes = sorted(self.class_mapping.items(), key=lambda x: x[1])

        with open(classes_file, "w") as f:
            for class_name, _class_id in sorted_classes:
                f.write(f"{class_name}\n")

    def bbox_to_yolo_format(
        self, bbox: dict[str, float], img_width: int, img_height: int
    ) -> tuple[float, float, float, float]:
        """Convert bounding box to YOLO format.

        Args:
            bbox: Bounding box dictionary with x_min, y_min, x_max, y_max
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            Tuple of (center_x, center_y, width, height) normalized to [0, 1]
        """
        # Calculate center and dimensions
        center_x = (bbox["x_min"] + bbox["x_max"]) / 2.0
        center_y = (bbox["y_min"] + bbox["y_max"]) / 2.0
        width = bbox["x_max"] - bbox["x_min"]
        height = bbox["y_max"] - bbox["y_min"]

        # Normalize to [0, 1]
        center_x_norm = center_x / img_width
        center_y_norm = center_y / img_height
        width_norm = width / img_width
        height_norm = height / img_height

        # Clamp to valid range
        center_x_norm = max(0, min(1, center_x_norm))
        center_y_norm = max(0, min(1, center_y_norm))
        width_norm = max(0, min(1, width_norm))
        height_norm = max(0, min(1, height_norm))

        return center_x_norm, center_y_norm, width_norm, height_norm

    def export_frame_annotations(
        self,
        frame_id: int,
        detections: list[dict[str, Any]],
        img_width: int,
        img_height: int,
    ) -> str:
        """Export annotations for a single frame.

        Args:
            frame_id: Frame identifier
            detections: List of detection dictionaries
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            Path to created YOLO label file
        """
        label_file = self.output_dir / f"frame_{frame_id:06d}.txt"

        with open(label_file, "w") as f:
            for detection in detections:
                class_name = detection.get("class_name", "unknown")

                # Skip unknown classes
                if class_name not in self.class_mapping:
                    continue

                class_id = self.class_mapping[class_name]
                bbox = detection.get("bbox_2d")

                if not bbox:
                    continue

                # Convert to YOLO format
                center_x, center_y, width, height = self.bbox_to_yolo_format(
                    bbox, img_width, img_height
                )

                # Write YOLO line
                f.write(
                    f"{class_id} {center_x:.6f} {center_y:.6f} {width:.6f} {height:.6f}\n"
                )

        return str(label_file)

    def export_dataset_annotations(
        self, dataset_info: dict[str, Any]
    ) -> dict[str, str]:
        """Export annotations for entire dataset.

        Args:
            dataset_info: Dataset information with frames and detections

        Returns:
            Dictionary with export statistics and file paths
        """
        stats = {
            "total_frames": 0,
            "total_detections": 0,
            "classes_found": set(),
            "label_files": [],
        }

        frames = dataset_info.get("frames", [])

        for frame_data in frames:
            frame_id = frame_data.get("frame_id", 0)
            detections = frame_data.get("detections", [])
            img_width = frame_data.get("width", 1280)
            img_height = frame_data.get("height", 720)

            # Export frame annotations
            label_file = self.export_frame_annotations(
                frame_id, detections, img_width, img_height
            )

            stats["label_files"].append(label_file)
            stats["total_frames"] += 1
            stats["total_detections"] += len(detections)

            # Track classes
            for detection in detections:
                class_name = detection.get("class_name")
                if class_name:
                    stats["classes_found"].add(class_name)

        # Convert set to list for JSON serialization
        stats["classes_found"] = list(stats["classes_found"])

        # Save export statistics
        stats_file = self.output_dir / "export_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        print("YOLO export complete:")
        print(f"  - {stats['total_frames']} frames")
        print(f"  - {stats['total_detections']} detections")
        print(f"  - {len(stats['classes_found'])} classes: {stats['classes_found']}")

        return stats

    def detect_pallet_faces_and_holes(
        self, pallet_obj: Any, camera_obj: Any, img_width: int, img_height: int
    ) -> list[dict[str, Any]]:
        """Detect pallet faces and holes for YOLO annotation.

        Args:
            pallet_obj: Blender pallet object
            camera_obj: Blender camera object
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            List of detection dictionaries for faces and holes
        """
        if not BLENDER_AVAILABLE:
            return []

        detections = []

        # Get pallet bounding box
        pallet_bbox = self._get_object_bbox_2d(
            pallet_obj, camera_obj, img_width, img_height
        )

        if pallet_bbox:
            # Add pallet detection
            detections.append(
                {
                    "class_name": "pallet",
                    "bbox_2d": pallet_bbox,
                    "confidence": 1.0,
                    "object_name": pallet_obj.name,
                }
            )

            # Detect faces (simplified - based on viewing angle)
            face_detections = self._detect_pallet_faces(
                pallet_obj, camera_obj, pallet_bbox, img_width, img_height
            )
            detections.extend(face_detections)

            # Detect holes in visible faces
            hole_detections = self._detect_pallet_holes(
                pallet_obj, camera_obj, face_detections, img_width, img_height
            )
            detections.extend(hole_detections)

        return detections

    def _get_object_bbox_2d(
        self, obj: Any, camera_obj: Any, img_width: int, img_height: int
    ) -> dict[str, float] | None:
        """Get 2D bounding box of object in camera view.

        Args:
            obj: Blender object
            camera_obj: Blender camera object
            img_width: Image width
            img_height: Image height

        Returns:
            Bounding box dictionary or None if not visible
        """
        if not BLENDER_AVAILABLE:
            return None

        # Get object vertices in world space
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)

        try:
            mesh = obj_eval.to_mesh()
            vertices_world = [obj_eval.matrix_world @ v.co for v in mesh.vertices]
            obj_eval.to_mesh_clear()
        except Exception:
            # Fallback to bounding box corners
            vertices_world = [
                obj.matrix_world @ Vector(corner) for corner in obj.bound_box
            ]

        if not vertices_world:
            return None

        # Project vertices to camera space
        scene = bpy.context.scene
        projected_points = []

        for vertex in vertices_world:
            # Project to camera view
            co_2d = w2cv(scene, camera_obj, vertex)

            if co_2d.z > 0:  # In front of camera
                x = co_2d.x * img_width
                y = (1 - co_2d.y) * img_height  # Flip Y coordinate
                projected_points.append((x, y))

        if not projected_points:
            return None

        # Calculate bounding box
        xs, ys = zip(*projected_points, strict=False)
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        # Clamp to image bounds
        x_min = max(0, min(img_width, x_min))
        x_max = max(0, min(img_width, x_max))
        y_min = max(0, min(img_height, y_min))
        y_max = max(0, min(img_height, y_max))

        # Check if bounding box is valid
        if x_max <= x_min or y_max <= y_min:
            return None

        return {
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "width": x_max - x_min,
            "height": y_max - y_min,
        }

    def _detect_pallet_faces(
        self,
        pallet_obj: Any,
        camera_obj: Any,
        pallet_bbox: dict[str, float],
        img_width: int,  # noqa: ARG002
        img_height: int,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Detect visible pallet faces.

        Args:
            pallet_obj: Blender pallet object
            camera_obj: Blender camera object
            pallet_bbox: Pallet bounding box
            img_width: Image width
            img_height: Image height

        Returns:
            List of face detections
        """
        face_detections = []

        # Simplified face detection based on camera angle
        # In a real implementation, this would analyze mesh faces

        # Calculate viewing angle
        pallet_pos = Vector(pallet_obj.location)
        camera_pos = Vector(camera_obj.location)
        view_vector = (pallet_pos - camera_pos).normalized()

        # Estimate face visibility based on viewing angle
        angle_y = abs(view_vector.y)
        angle_x = abs(view_vector.x)

        face_size_factor = 0.4  # Faces are ~40% of pallet size

        # Front/back face
        if angle_y > 0.3:
            face_width = pallet_bbox["width"] * face_size_factor
            face_height = pallet_bbox["height"] * 0.8

            center_x = pallet_bbox["x_min"] + pallet_bbox["width"] / 2
            center_y = pallet_bbox["y_min"] + pallet_bbox["height"] / 2

            face_detections.append(
                {
                    "class_name": "pallet_face",
                    "bbox_2d": {
                        "x_min": center_x - face_width / 2,
                        "y_min": center_y - face_height / 2,
                        "x_max": center_x + face_width / 2,
                        "y_max": center_y + face_height / 2,
                        "width": face_width,
                        "height": face_height,
                    },
                    "face_type": "front" if view_vector.y > 0 else "back",
                    "confidence": 0.9,
                }
            )

        # Side faces
        if angle_x > 0.3:
            face_width = pallet_bbox["width"] * 0.8
            face_height = pallet_bbox["height"] * face_size_factor

            center_x = pallet_bbox["x_min"] + pallet_bbox["width"] / 2
            center_y = pallet_bbox["y_min"] + pallet_bbox["height"] / 2

            face_detections.append(
                {
                    "class_name": "pallet_face",
                    "bbox_2d": {
                        "x_min": center_x - face_width / 2,
                        "y_min": center_y - face_height / 2,
                        "x_max": center_x + face_width / 2,
                        "y_max": center_y + face_height / 2,
                        "width": face_width,
                        "height": face_height,
                    },
                    "face_type": "left" if view_vector.x > 0 else "right",
                    "confidence": 0.9,
                }
            )

        return face_detections

    def _detect_pallet_holes(
        self,
        pallet_obj: Any,  # noqa: ARG002
        camera_obj: Any,  # noqa: ARG002
        face_detections: list[dict[str, Any]],
        img_width: int,  # noqa: ARG002
        img_height: int,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        """Detect holes in visible pallet faces.

        Args:
            pallet_obj: Blender pallet object
            camera_obj: Blender camera object
            face_detections: List of detected faces
            img_width: Image width
            img_height: Image height

        Returns:
            List of hole detections
        """
        hole_detections = []

        # Standard pallet has holes arranged in grid pattern
        # holes_per_face = 8  # 4x2 grid typically - unused for now
        hole_size_factor = 0.15  # Holes are ~15% of face size

        for face_data in face_detections:
            face_bbox = face_data["bbox_2d"]
            face_type = face_data.get("face_type", "unknown")

            # Calculate hole positions within face
            if face_type in ["front", "back"]:
                # 4 holes horizontally, 2 vertically
                holes_x, holes_y = 4, 2
            else:
                # 2 holes horizontally, 4 vertically for side faces
                holes_x, holes_y = 2, 4

            hole_width = face_bbox["width"] / holes_x * hole_size_factor
            hole_height = face_bbox["height"] / holes_y * hole_size_factor

            spacing_x = face_bbox["width"] / holes_x
            spacing_y = face_bbox["height"] / holes_y

            for row in range(holes_y):
                for col in range(holes_x):
                    # Calculate hole center
                    hole_center_x = face_bbox["x_min"] + spacing_x * (col + 0.5)
                    hole_center_y = face_bbox["y_min"] + spacing_y * (row + 0.5)

                    hole_detections.append(
                        {
                            "class_name": "hole",
                            "bbox_2d": {
                                "x_min": hole_center_x - hole_width / 2,
                                "y_min": hole_center_y - hole_height / 2,
                                "x_max": hole_center_x + hole_width / 2,
                                "y_max": hole_center_y + hole_height / 2,
                                "width": hole_width,
                                "height": hole_height,
                            },
                            "hole_id": row * holes_x + col,
                            "face_type": face_type,
                            "confidence": 0.8,
                        }
                    )

        return hole_detections

    def create_training_split(
        self, train_ratio: float = 0.8, val_ratio: float = 0.15
    ) -> dict[str, list[str]]:
        """Create train/validation/test split for YOLO training.

        Args:
            train_ratio: Ratio of data for training
            val_ratio: Ratio of data for validation (rest goes to test)

        Returns:
            Dictionary with train/val/test file lists
        """
        import random

        # Get all label files
        label_files = list(self.output_dir.glob("frame_*.txt"))
        label_files.sort()

        # Shuffle for random split
        random.shuffle(label_files)

        total_files = len(label_files)
        train_count = int(total_files * train_ratio)
        val_count = int(total_files * val_ratio)

        splits = {
            "train": [str(f) for f in label_files[:train_count]],
            "val": [str(f) for f in label_files[train_count : train_count + val_count]],
            "test": [str(f) for f in label_files[train_count + val_count :]],
        }

        # Save split information
        split_file = self.output_dir / "dataset_split.json"
        with open(split_file, "w") as f:
            json.dump(splits, f, indent=2)

        print("Dataset split created:")
        print(f"  - Train: {len(splits['train'])} files")
        print(f"  - Val: {len(splits['val'])} files")
        print(f"  - Test: {len(splits['test'])} files")

        return splits
