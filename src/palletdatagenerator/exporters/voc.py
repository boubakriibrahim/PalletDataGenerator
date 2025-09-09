"""VOC (PASCAL Visual Object Classes) format exporter."""

import os
import xml.etree.ElementTree as ET  # nosec B405
from pathlib import Path
from typing import Any

try:
    from pascal_voc_writer import Writer as VocWriter

    VOC_WRITER_AVAILABLE = True
except ImportError:
    VOC_WRITER_AVAILABLE = False


class VOCExporter:
    """Export annotations in PASCAL VOC XML format.

    VOC format uses XML files with one file per image containing
    all object annotations for that image.
    """

    def __init__(self, output_dir: str, images_dir: str = "images"):
        """Initialize VOC exporter.

        Args:
            output_dir: Directory to save VOC XML files
            images_dir: Directory containing the images (for XML references)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = images_dir

        if not VOC_WRITER_AVAILABLE:
            print(
                "Warning: pascal_voc_writer not available, using manual XML generation"
            )

    def export_frame_annotations(
        self,
        frame_id: int,
        image_path: str,
        detections: list[dict[str, Any]],
        img_width: int,
        img_height: int,
    ) -> str:
        """Export annotations for a single frame in VOC format.

        Args:
            frame_id: Frame identifier
            image_path: Path to the image file
            detections: List of detection dictionaries
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            Path to created VOC XML file
        """
        image_filename = os.path.basename(image_path)
        xml_filename = f"frame_{frame_id:06d}.xml"
        xml_path = self.output_dir / xml_filename

        if VOC_WRITER_AVAILABLE:
            return self._export_with_voc_writer(
                xml_path, image_filename, detections, img_width, img_height
            )
        else:
            return self._export_manual_xml(
                xml_path, image_filename, detections, img_width, img_height
            )

    def _export_with_voc_writer(
        self,
        xml_path: Path,
        image_filename: str,  # noqa: ARG002
        detections: list[dict[str, Any]],
        img_width: int,
        img_height: int,
    ) -> str:
        """Export using pascal_voc_writer library.

        Args:
            xml_path: Path for output XML file
            image_filename: Name of the image file
            detections: List of detection dictionaries
            img_width: Image width
            img_height: Image height

        Returns:
            Path to created XML file
        """
        writer = VocWriter(
            path=self.images_dir,
            width=img_width,
            height=img_height,
            depth=3,  # RGB images
        )

        # Add objects
        for detection in detections:
            class_name = detection.get("class_name", "unknown")
            bbox = detection.get("bbox_2d")

            if not bbox:
                continue

            # VOC format uses (xmin, ymin, xmax, ymax)
            xmin = int(bbox["x_min"])
            ymin = int(bbox["y_min"])
            xmax = int(bbox["x_max"])
            ymax = int(bbox["y_max"])

            # Ensure coordinates are within image bounds
            xmin = max(0, min(img_width - 1, xmin))
            ymin = max(0, min(img_height - 1, ymin))
            xmax = max(xmin + 1, min(img_width, xmax))
            ymax = max(ymin + 1, min(img_height, ymax))

            writer.addObject(
                name=class_name, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax, difficult=0
            )

        # Save XML file
        writer.save(str(xml_path.with_suffix("")))  # Writer adds .xml extension

        return str(xml_path)

    def _export_manual_xml(
        self,
        xml_path: Path,
        image_filename: str,
        detections: list[dict[str, Any]],
        img_width: int,
        img_height: int,
    ) -> str:
        """Export VOC XML manually without external library.

        Args:
            xml_path: Path for output XML file
            image_filename: Name of the image file
            detections: List of detection dictionaries
            img_width: Image width
            img_height: Image height

        Returns:
            Path to created XML file
        """
        # Create root element
        annotation = ET.Element("annotation")

        # Add folder
        folder = ET.SubElement(annotation, "folder")
        folder.text = self.images_dir

        # Add filename
        filename = ET.SubElement(annotation, "filename")
        filename.text = image_filename

        # Add path
        path = ET.SubElement(annotation, "path")
        path.text = os.path.join(self.images_dir, image_filename)

        # Add source
        source = ET.SubElement(annotation, "source")
        database = ET.SubElement(source, "database")
        database.text = "PalletDataGenerator"

        # Add size
        size = ET.SubElement(annotation, "size")
        width = ET.SubElement(size, "width")
        width.text = str(img_width)
        height = ET.SubElement(size, "height")
        height.text = str(img_height)
        depth = ET.SubElement(size, "depth")
        depth.text = "3"

        # Add segmented
        segmented = ET.SubElement(annotation, "segmented")
        segmented.text = "0"

        # Add objects
        for detection in detections:
            class_name = detection.get("class_name", "unknown")
            bbox = detection.get("bbox_2d")

            if not bbox:
                continue

            obj = ET.SubElement(annotation, "object")

            # Add name
            name = ET.SubElement(obj, "name")
            name.text = class_name

            # Add pose
            pose = ET.SubElement(obj, "pose")
            pose.text = "Unspecified"

            # Add truncated
            truncated = ET.SubElement(obj, "truncated")
            truncated.text = "0"

            # Add difficult
            difficult = ET.SubElement(obj, "difficult")
            difficult.text = "0"

            # Add bounding box
            bndbox = ET.SubElement(obj, "bndbox")

            # Ensure coordinates are integers and within bounds
            xmin = max(0, min(img_width - 1, int(bbox["x_min"])))
            ymin = max(0, min(img_height - 1, int(bbox["y_min"])))
            xmax = max(xmin + 1, min(img_width, int(bbox["x_max"])))
            ymax = max(ymin + 1, min(img_height, int(bbox["y_max"])))

            xmin_elem = ET.SubElement(bndbox, "xmin")
            xmin_elem.text = str(xmin)
            ymin_elem = ET.SubElement(bndbox, "ymin")
            ymin_elem.text = str(ymin)
            xmax_elem = ET.SubElement(bndbox, "xmax")
            xmax_elem.text = str(xmax)
            ymax_elem = ET.SubElement(bndbox, "ymax")
            ymax_elem.text = str(ymax)

        # Write XML file
        tree = ET.ElementTree(annotation)
        ET.indent(tree, space="  ", level=0)  # Pretty print (Python 3.9+)
        tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

        return str(xml_path)

    def export_dataset_annotations(
        self, dataset_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Export complete dataset annotations in VOC format.

        Args:
            dataset_info: Dataset information with frames and detections

        Returns:
            Dictionary with export statistics
        """
        stats = {
            "total_frames": 0,
            "total_detections": 0,
            "classes_found": set(),
            "xml_files": [],
        }

        frames = dataset_info.get("frames", [])

        for frame_data in frames:
            frame_id = frame_data.get("frame_id", 0)
            image_path = frame_data.get("image_path", f"frame_{frame_id:06d}.png")
            detections = frame_data.get("detections", [])
            img_width = frame_data.get("width", 1280)
            img_height = frame_data.get("height", 720)

            # Export frame annotations
            xml_file = self.export_frame_annotations(
                frame_id, image_path, detections, img_width, img_height
            )

            stats["xml_files"].append(xml_file)
            stats["total_frames"] += 1
            stats["total_detections"] += len(detections)

            # Track classes
            for detection in detections:
                class_name = detection.get("class_name")
                if class_name:
                    stats["classes_found"].add(class_name)

        # Convert set to list for JSON serialization
        stats["classes_found"] = list(stats["classes_found"])

        # Create classes.txt file
        self._create_classes_file(stats["classes_found"])

        # Save export statistics
        import json

        stats_file = self.output_dir / "voc_export_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2, default=str)

        print("VOC export complete:")
        print(f"  - {stats['total_frames']} XML files")
        print(f"  - {stats['total_detections']} total detections")
        print(f"  - {len(stats['classes_found'])} classes: {stats['classes_found']}")

        return stats

    def _create_classes_file(self, classes: list[str]) -> None:
        """Create classes.txt file listing all classes.

        Args:
            classes: List of class names found in the dataset
        """
        classes_file = self.output_dir / "classes.txt"

        with open(classes_file, "w") as f:
            for class_name in sorted(classes):
                f.write(f"{class_name}\n")

    def create_train_val_split(self, train_ratio: float = 0.8) -> dict[str, list[str]]:
        """Create train/validation split for VOC format.

        Args:
            train_ratio: Ratio of data for training (rest goes to validation)

        Returns:
            Dictionary with train and validation file lists
        """
        import random

        # Get all XML files
        xml_files = list(self.output_dir.glob("frame_*.xml"))
        xml_files.sort()

        # Extract base names (without extension)
        base_names = [f.stem for f in xml_files]

        # Shuffle for random split
        random.shuffle(base_names)

        # Split
        total_files = len(base_names)
        train_count = int(total_files * train_ratio)

        train_files = base_names[:train_count]
        val_files = base_names[train_count:]

        # Save train/val splits
        train_file = self.output_dir / "train.txt"
        with open(train_file, "w") as f:
            for name in train_files:
                f.write(f"{name}\n")

        val_file = self.output_dir / "val.txt"
        with open(val_file, "w") as f:
            for name in val_files:
                f.write(f"{name}\n")

        splits = {"train": train_files, "val": val_files}

        print("VOC dataset split created:")
        print(f"  - Train: {len(train_files)} files")
        print(f"  - Val: {len(val_files)} files")

        return splits

    def validate_xml_files(self) -> dict[str, Any]:
        """Validate all XML files for common issues.

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "valid_files": 0,
            "invalid_files": 0,
            "issues": [],
            "warnings": [],
        }

        xml_files = list(self.output_dir.glob("*.xml"))

        for xml_file in xml_files:
            try:
                tree = ET.parse(xml_file)  # nosec B314
                root = tree.getroot()

                # Check if it's a valid VOC annotation
                if root.tag != "annotation":
                    validation_results["invalid_files"] += 1
                    validation_results["issues"].append(
                        f"{xml_file.name}: Root element is not 'annotation'"
                    )
                    continue

                # Check for required elements
                required_elements = ["filename", "size", "object"]
                missing_elements = []

                for element in required_elements:
                    if root.find(element) is None and element != "object":
                        missing_elements.append(element)

                if missing_elements:
                    validation_results["warnings"].append(
                        f"{xml_file.name}: Missing elements: {missing_elements}"
                    )

                # Check objects
                objects = root.findall("object")
                for obj in objects:
                    name_elem = obj.find("name")
                    bndbox_elem = obj.find("bndbox")

                    if name_elem is None:
                        validation_results["issues"].append(
                            f"{xml_file.name}: Object missing name"
                        )
                        continue

                    if bndbox_elem is None:
                        validation_results["issues"].append(
                            f"{xml_file.name}: Object missing bounding box"
                        )
                        continue

                    # Check bounding box coordinates
                    coords = ["xmin", "ymin", "xmax", "ymax"]
                    for coord in coords:
                        coord_elem = bndbox_elem.find(coord)
                        if coord_elem is None:
                            validation_results["issues"].append(
                                f"{xml_file.name}: Missing {coord} in bounding box"
                            )
                        else:
                            try:
                                float(coord_elem.text)
                            except (ValueError, TypeError):
                                validation_results["issues"].append(
                                    f"{xml_file.name}: Invalid {coord} value: {coord_elem.text}"
                                )

                validation_results["valid_files"] += 1

            except ET.ParseError as e:
                validation_results["invalid_files"] += 1
                validation_results["issues"].append(
                    f"{xml_file.name}: XML parse error: {e}"
                )
            except Exception as e:
                validation_results["invalid_files"] += 1
                validation_results["issues"].append(
                    f"{xml_file.name}: Validation error: {e}"
                )

        validation_results["total_files"] = len(xml_files)

        return validation_results
