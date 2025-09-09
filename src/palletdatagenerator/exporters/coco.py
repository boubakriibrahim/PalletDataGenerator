"""COCO format exporter for object detection and segmentation annotations."""

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import importlib.util

    BLENDER_AVAILABLE = importlib.util.find_spec("bpy") is not None
    if BLENDER_AVAILABLE:
        import bpy
        from mathutils import Vector
except ImportError:
    BLENDER_AVAILABLE = False


class COCOExporter:
    """Export annotations in COCO (Common Objects in Context) format.

    COCO format is widely used for object detection, segmentation, and keypoint detection.
    This exporter focuses on object detection with bounding boxes.
    """

    def __init__(self, output_dir: str, dataset_name: str = "PalletDataset"):
        """Initialize COCO exporter.

        Args:
            output_dir: Directory to save COCO annotation files
            dataset_name: Name of the dataset for metadata
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_name = dataset_name

        # Initialize COCO structure
        self.coco_data = {
            "info": self._create_info(),
            "licenses": self._create_licenses(),
            "categories": self._create_categories(),
            "images": [],
            "annotations": [],
        }

        self.image_id = 1
        self.annotation_id = 1

    def _create_info(self) -> dict[str, Any]:
        """Create COCO info section.

        Returns:
            Info dictionary with dataset metadata
        """
        return {
            "description": f"{self.dataset_name} - Synthetic pallet dataset",
            "url": "https://github.com/boubakriibrahim/PalletDataGenerator",
            "version": "0.1.0",
            "year": datetime.datetime.now().year,
            "contributor": "PalletDataGenerator",
            "date_created": datetime.datetime.now().isoformat(),
        }

    def _create_licenses(self) -> list[dict[str, Any]]:
        """Create COCO licenses section.

        Returns:
            List of license dictionaries
        """
        return [
            {
                "id": 1,
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT",
            }
        ]

    def _create_categories(self) -> list[dict[str, Any]]:
        """Create COCO categories section.

        Returns:
            List of category dictionaries
        """
        return [
            {"id": 1, "name": "pallet", "supercategory": "logistics"},
            {"id": 2, "name": "pallet_face", "supercategory": "pallet_part"},
            {"id": 3, "name": "hole", "supercategory": "pallet_part"},
            {"id": 4, "name": "box", "supercategory": "cargo"},
        ]

    def add_image(
        self, image_path: str, width: int, height: int, frame_id: int | None = None
    ) -> int:
        """Add image to COCO dataset.

        Args:
            image_path: Path to the image file
            width: Image width in pixels
            height: Image height in pixels
            frame_id: Optional frame identifier

        Returns:
            Image ID assigned to this image
        """
        image_filename = os.path.basename(image_path)

        image_data = {
            "id": self.image_id,
            "width": width,
            "height": height,
            "file_name": image_filename,
            "license": 1,
            "flickr_url": "",
            "coco_url": "",
            "date_captured": datetime.datetime.now().isoformat(),
        }

        if frame_id is not None:
            image_data["frame_id"] = frame_id

        self.coco_data["images"].append(image_data)

        current_image_id = self.image_id
        self.image_id += 1

        return current_image_id

    def add_annotation(
        self,
        image_id: int,
        category_name: str,
        bbox: dict[str, float],
        segmentation: list | None = None,
        area: float | None = None,
        iscrowd: int = 0,
    ) -> int:
        """Add annotation to COCO dataset.

        Args:
            image_id: ID of the image this annotation belongs to
            category_name: Name of the object category
            bbox: Bounding box in format [x, y, width, height]
            segmentation: Optional segmentation polygon
            area: Optional area of the annotation
            iscrowd: Whether this is a crowd annotation (0 or 1)

        Returns:
            Annotation ID assigned to this annotation
        """
        # Find category ID
        category_id = None
        for category in self.coco_data["categories"]:
            if category["name"] == category_name:
                category_id = category["id"]
                break

        if category_id is None:
            print(f"Warning: Unknown category '{category_name}', skipping annotation")
            return -1

        # Convert bbox format from {x_min, y_min, x_max, y_max} to [x, y, width, height]
        if "x_min" in bbox:
            coco_bbox = [bbox["x_min"], bbox["y_min"], bbox["width"], bbox["height"]]
        else:
            coco_bbox = bbox

        # Calculate area if not provided
        if area is None:
            area = coco_bbox[2] * coco_bbox[3]  # width * height

        annotation_data = {
            "id": self.annotation_id,
            "image_id": image_id,
            "category_id": category_id,
            "segmentation": segmentation or [],
            "area": area,
            "bbox": coco_bbox,
            "iscrowd": iscrowd,
        }

        self.coco_data["annotations"].append(annotation_data)

        current_annotation_id = self.annotation_id
        self.annotation_id += 1

        return current_annotation_id

    def export_frame_annotations(
        self,
        frame_id: int,
        image_path: str,
        detections: list[dict[str, Any]],
        img_width: int,
        img_height: int,
    ) -> int:
        """Export annotations for a single frame.

        Args:
            frame_id: Frame identifier
            image_path: Path to the image file
            detections: List of detection dictionaries
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            Image ID assigned to this frame
        """
        # Add image to dataset
        image_id = self.add_image(image_path, img_width, img_height, frame_id)

        # Add annotations for this image
        for detection in detections:
            class_name = detection.get("class_name", "unknown")
            bbox = detection.get("bbox_2d")

            if not bbox:
                continue

            # Add annotation
            self.add_annotation(
                image_id=image_id,
                category_name=class_name,
                bbox=bbox,
                area=bbox.get("area", bbox["width"] * bbox["height"]),
            )

        return image_id

    def export_dataset_annotations(self, dataset_info: dict[str, Any]) -> str:
        """Export complete dataset annotations to COCO format.

        Args:
            dataset_info: Dataset information with frames and detections

        Returns:
            Path to exported COCO annotation file
        """
        frames = dataset_info.get("frames", [])

        for frame_data in frames:
            frame_id = frame_data.get("frame_id", 0)
            image_path = frame_data.get("image_path", f"frame_{frame_id:06d}.png")
            detections = frame_data.get("detections", [])
            img_width = frame_data.get("width", 1280)
            img_height = frame_data.get("height", 720)

            self.export_frame_annotations(
                frame_id, image_path, detections, img_width, img_height
            )

        # Save COCO annotations
        output_file = self.output_dir / "annotations.json"
        with open(output_file, "w") as f:
            json.dump(self.coco_data, f, indent=2)

        # Save statistics
        stats = self._generate_statistics()
        stats_file = self.output_dir / "coco_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        print("COCO export complete:")
        print(f"  - {len(self.coco_data['images'])} images")
        print(f"  - {len(self.coco_data['annotations'])} annotations")
        print(f"  - {len(self.coco_data['categories'])} categories")
        print(f"  - Saved to: {output_file}")

        return str(output_file)

    def _generate_statistics(self) -> dict[str, Any]:
        """Generate statistics about the exported dataset.

        Returns:
            Dictionary with dataset statistics
        """
        stats = {
            "total_images": len(self.coco_data["images"]),
            "total_annotations": len(self.coco_data["annotations"]),
            "categories": {},
        }

        # Count annotations per category
        for annotation in self.coco_data["annotations"]:
            category_id = annotation["category_id"]

            # Find category name
            category_name = "unknown"
            for category in self.coco_data["categories"]:
                if category["id"] == category_id:
                    category_name = category["name"]
                    break

            if category_name not in stats["categories"]:
                stats["categories"][category_name] = {
                    "count": 0,
                    "total_area": 0,
                    "avg_area": 0,
                }

            stats["categories"][category_name]["count"] += 1
            stats["categories"][category_name]["total_area"] += annotation["area"]

        # Calculate average areas
        for _category_name, category_stats in stats["categories"].items():
            if category_stats["count"] > 0:
                category_stats["avg_area"] = (
                    category_stats["total_area"] / category_stats["count"]
                )

        return stats

    def create_dataset_splits(
        self, train_ratio: float = 0.8, val_ratio: float = 0.15
    ) -> dict[str, Any]:
        """Create train/validation/test splits in COCO format.

        Args:
            train_ratio: Ratio of data for training
            val_ratio: Ratio of data for validation

        Returns:
            Dictionary with information about created splits
        """
        import random

        # Get all images
        all_images = self.coco_data["images"].copy()
        random.shuffle(all_images)

        total_images = len(all_images)
        train_count = int(total_images * train_ratio)
        val_count = int(total_images * val_ratio)

        # Split images
        train_images = all_images[:train_count]
        val_images = all_images[train_count : train_count + val_count]
        test_images = all_images[train_count + val_count :]

        splits_info = {
            "train": {"image_count": len(train_images), "annotation_count": 0},
            "val": {"image_count": len(val_images), "annotation_count": 0},
            "test": {"image_count": len(test_images), "annotation_count": 0},
        }

        # Create separate COCO files for each split
        for split_name, split_images in [
            ("train", train_images),
            ("val", val_images),
            ("test", test_images),
        ]:
            if not split_images:
                continue

            # Get image IDs for this split
            split_image_ids = {img["id"] for img in split_images}

            # Filter annotations for this split
            split_annotations = [
                ann
                for ann in self.coco_data["annotations"]
                if ann["image_id"] in split_image_ids
            ]

            splits_info[split_name]["annotation_count"] = len(split_annotations)

            # Create COCO structure for this split
            split_coco = {
                "info": self.coco_data["info"].copy(),
                "licenses": self.coco_data["licenses"],
                "categories": self.coco_data["categories"],
                "images": split_images,
                "annotations": split_annotations,
            }

            # Update info for split
            split_coco["info"]["description"] += f" - {split_name.upper()} split"

            # Save split file
            split_file = self.output_dir / f"annotations_{split_name}.json"
            with open(split_file, "w") as f:
                json.dump(split_coco, f, indent=2)

        # Save split information
        split_info_file = self.output_dir / "dataset_splits_info.json"
        with open(split_info_file, "w") as f:
            json.dump(splits_info, f, indent=2)

        print("COCO dataset splits created:")
        for split_name, split_info in splits_info.items():
            print(
                f"  - {split_name}: {split_info['image_count']} images, "
                f"{split_info['annotation_count']} annotations"
            )

        return splits_info

    def validate_annotations(self) -> dict[str, Any]:
        """Validate COCO annotations for common issues.

        Returns:
            Dictionary with validation results and issues found
        """
        validation_results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "statistics": {},
        }

        # Check for duplicate image IDs
        image_ids = [img["id"] for img in self.coco_data["images"]]
        if len(image_ids) != len(set(image_ids)):
            validation_results["valid"] = False
            validation_results["issues"].append("Duplicate image IDs found")

        # Check for duplicate annotation IDs
        annotation_ids = [ann["id"] for ann in self.coco_data["annotations"]]
        if len(annotation_ids) != len(set(annotation_ids)):
            validation_results["valid"] = False
            validation_results["issues"].append("Duplicate annotation IDs found")

        # Check for annotations referencing non-existent images
        valid_image_ids = set(image_ids)
        orphaned_annotations = [
            ann
            for ann in self.coco_data["annotations"]
            if ann["image_id"] not in valid_image_ids
        ]
        if orphaned_annotations:
            validation_results["valid"] = False
            validation_results["issues"].append(
                f"{len(orphaned_annotations)} annotations reference non-existent images"
            )

        # Check for invalid bounding boxes
        invalid_bboxes = []
        for ann in self.coco_data["annotations"]:
            bbox = ann["bbox"]
            if (
                len(bbox) != 4
                or any(val < 0 for val in bbox)
                or bbox[2] <= 0
                or bbox[3] <= 0
            ):
                invalid_bboxes.append(ann["id"])

        if invalid_bboxes:
            validation_results["valid"] = False
            validation_results["issues"].append(
                f"{len(invalid_bboxes)} annotations have invalid bounding boxes"
            )

        # Generate statistics
        validation_results["statistics"] = {
            "total_images": len(self.coco_data["images"]),
            "total_annotations": len(self.coco_data["annotations"]),
            "categories_used": len(
                {ann["category_id"] for ann in self.coco_data["annotations"]}
            ),
            "avg_annotations_per_image": (
                len(self.coco_data["annotations"]) / len(self.coco_data["images"])
                if self.coco_data["images"]
                else 0
            ),
        }

        return validation_results
