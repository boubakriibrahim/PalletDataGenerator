"""Utility functions for PalletDataGenerator."""

import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_file: Optional log file path
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Setup file handler if specified
    handlers = [console_handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if necessary.

    Args:
        path: Directory path to create

    Returns:
        Path object for the directory
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def load_config(config_path: str) -> dict[str, Any]:
    """Load configuration from JSON or YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file format is invalid
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                try:
                    import yaml

                    return yaml.safe_load(f)
                except ImportError as import_err:
                    raise ValueError(
                        "PyYAML required for YAML config files"
                    ) from import_err
            else:
                return json.load(f)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid configuration file format: {e}") from e


def save_config(config: dict[str, Any], config_path: str) -> None:
    """Save configuration to JSON file.

    Args:
        config: Configuration dictionary to save
        config_path: Path to save configuration file
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, default=str)


def set_random_seed(seed: int) -> None:
    """Set random seed for reproducible results.

    Args:
        seed: Random seed value
    """
    random.seed(seed)

    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass

    # Set Blender random seed if available
    try:
        import bpy

        bpy.context.scene.frame_set(seed % 1000)
    except ImportError:
        pass


def validate_blender_environment() -> bool:
    """Validate that Blender environment is available and properly configured.

    Returns:
        True if Blender environment is valid, False otherwise
    """
    try:
        import bpy
        from bpy_extras.object_utils import world_to_camera_view
        from mathutils import Euler, Matrix, Vector

        # Check if we have a scene
        if not bpy.context.scene:
            logger.error("No active Blender scene found")
            return False

        # Check for Cycles addon
        if "cycles" not in bpy.context.preferences.addons:
            logger.warning("Cycles addon not found, some features may be limited")

        logger.info("Blender environment validation successful")
        return True

    except ImportError as e:
        logger.error(f"Blender Python API not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Blender environment validation failed: {e}")
        return False


def get_blender_version() -> tuple[int, int, int] | None:
    """Get Blender version information.

    Returns:
        Tuple of (major, minor, patch) version numbers or None if not available
    """
    try:
        import bpy

        return bpy.app.version
    except ImportError:
        return None


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    # Format as integer if it's a whole number, otherwise with one decimal
    if size_bytes == int(size_bytes):
        return f"{int(size_bytes)} {size_names[i]}"
    return f"{size_bytes:.1f} {size_names[i]}"


def get_system_info() -> dict[str, Any]:
    """Get system information for debugging and logging.

    Returns:
        Dictionary with system information
    """
    import platform

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.architecture(),
        "processor": platform.processor(),
    }

    # Add Blender info if available
    blender_version = get_blender_version()
    if blender_version:
        info["blender_version"] = ".".join(map(str, blender_version))

    # Add GPU info if available
    try:
        import bpy

        if "cycles" in bpy.context.preferences.addons:
            cycles_prefs = bpy.context.preferences.addons["cycles"].preferences
            devices = []
            for device in cycles_prefs.devices:
                devices.append(
                    {"name": device.name, "type": device.type, "use": device.use}
                )
            info["gpu_devices"] = devices
    except (ImportError, AttributeError):
        pass

    return info


def create_dataset_manifest(dataset_info: dict[str, Any], output_path: str) -> None:
    """Create a comprehensive dataset manifest file.

    Args:
        dataset_info: Dictionary containing dataset information
        output_path: Path to save the manifest file
    """
    import datetime

    manifest = {
        "dataset_info": dataset_info,
        "generation_timestamp": datetime.datetime.now().isoformat(),
        "generator_version": "0.1.0",  # Would be dynamically set
        "system_info": get_system_info(),
        "file_structure": {
            "images": "RGB rendered images",
            "depth": "Depth maps (16-bit PNG)",
            "normals": "Surface normal maps",
            "index": "Object index maps for segmentation",
            "yolo_labels": "YOLO format annotations",
            "voc_xml": "PASCAL VOC format annotations",
            "annotations.json": "COCO format annotations",
        },
    }

    # Add file counts and sizes
    output_dir = Path(output_path).parent
    if output_dir.exists():
        file_stats = {}
        for subdir in ["images", "depth", "normals", "index", "yolo_labels", "voc_xml"]:
            subdir_path = output_dir / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                file_stats[subdir] = {
                    "file_count": len([f for f in files if f.is_file()]),
                    "total_size": format_file_size(total_size),
                }
        manifest["file_statistics"] = file_stats

    # Save manifest
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    logger.info(f"Dataset manifest created: {output_path}")


def verify_dataset_integrity(dataset_dir: str) -> dict[str, Any]:
    """Verify dataset integrity by checking file consistency.

    Args:
        dataset_dir: Path to dataset directory

    Returns:
        Dictionary with verification results
    """
    dataset_path = Path(dataset_dir)
    results = {"valid": True, "issues": [], "warnings": [], "statistics": {}}

    if not dataset_path.exists():
        results["valid"] = False
        results["issues"].append(f"Dataset directory does not exist: {dataset_dir}")
        return results

    # Check for required subdirectories
    required_dirs = ["images"]
    optional_dirs = ["depth", "normals", "index", "yolo_labels", "voc_xml"]

    for req_dir in required_dirs:
        if not (dataset_path / req_dir).exists():
            results["valid"] = False
            results["issues"].append(f"Required directory missing: {req_dir}")

    # Count files in each directory
    file_counts = {}
    for dir_name in required_dirs + optional_dirs:
        dir_path = dataset_path / dir_name
        if dir_path.exists():
            files = list(dir_path.glob("*"))
            file_counts[dir_name] = len([f for f in files if f.is_file()])

    results["statistics"]["file_counts"] = file_counts

    # Check for consistency between directories
    if "images" in file_counts:
        image_count = file_counts["images"]
        for dir_name, count in file_counts.items():
            if dir_name != "images" and count != image_count:
                results["warnings"].append(
                    f"File count mismatch: {dir_name} has {count} files, "
                    f"but images has {image_count} files"
                )

    # Check for annotation files
    annotation_files = {
        "coco": dataset_path / "annotations.json",
        "manifest": dataset_path / "dataset_manifest.json",
    }

    for ann_type, ann_path in annotation_files.items():
        if ann_path.exists():
            results["statistics"][f"{ann_type}_annotation"] = True
        else:
            results["warnings"].append(f"Missing {ann_type} annotation file")

    return results


class ProgressTracker:
    """Progress tracking utility for long-running operations."""

    def __init__(self, total: int, description: str = "Processing"):
        """Initialize progress tracker.

        Args:
            total: Total number of items to process
            description: Description of the operation
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = None

    def start(self) -> None:
        """Start progress tracking."""
        import time

        self.start_time = time.time()
        logger.info(f"Starting {self.description}: 0/{self.total}")

    def update(self, increment: int = 1) -> None:
        """Update progress.

        Args:
            increment: Number of items processed since last update
        """
        import time

        self.current += increment

        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                rate = self.current / elapsed
                eta = (self.total - self.current) / rate if rate > 0 else 0

                logger.info(
                    f"{self.description}: {self.current}/{self.total} "
                    f"({self.current/self.total*100:.1f}%) "
                    f"- ETA: {eta:.1f}s"
                )

    def finish(self) -> None:
        """Finish progress tracking."""
        import time

        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info(
                f"{self.description} completed: {self.total} items in {elapsed:.1f}s"
            )
