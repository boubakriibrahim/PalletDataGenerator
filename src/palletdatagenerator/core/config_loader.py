"""Configuration loader for YAML configuration files."""

from pathlib import Path
from typing import Any

import yaml

from palletdatagenerator.core.generator import GenerationConfig


class ConfigLoader:
    """Load and validate configuration from YAML files."""

    def __init__(self, config_path: str):
        """Initialize configuration loader.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = Path(config_path)
        self._config_data: dict[str, Any] | None = None

    def load_config(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if self._config_data is None:
            if not self.config_path.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}"
                )

            with open(self.config_path) as f:
                self._config_data = yaml.safe_load(f)

        return self._config_data or {}

    def load_generation_config(self) -> GenerationConfig:
        """Load generation configuration from YAML file.

        Returns:
            GenerationConfig object
        """
        config_data = self.load_config()

        # Extract generation parameters with defaults
        generation_params = config_data.get("generation", {})

        return GenerationConfig(
            scene_type=generation_params.get("scene_type", "single_pallet"),
            num_frames=generation_params.get("num_frames", 100),
            resolution=tuple(generation_params.get("resolution", [640, 480])),
            output_dir=generation_params.get("output_dir", "./output"),
            export_formats=generation_params.get("export_formats", ["yolo"]),
            random_seed=generation_params.get("random_seed"),
            use_gpu=generation_params.get("use_gpu", False),
            samples=generation_params.get("samples", 128),
            pallet_count=generation_params.get("pallet_count", 1),
            box_count_range=tuple(generation_params.get("box_count_range", [5, 15])),
            train_ratio=generation_params.get("train_ratio", 0.7),
            val_ratio=generation_params.get("val_ratio", 0.2),
        )

    def get_section(self, section_name: str) -> dict[str, Any]:
        """Get a specific configuration section.

        Args:
            section_name: Name of the configuration section

        Returns:
            Configuration section dictionary
        """
        config_data = self.load_config()
        return config_data.get(section_name, {})

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found

        Returns:
            Configuration value
        """
        config_data = self.load_config()

        # Support dot notation for nested keys
        keys = key.split(".")
        value = config_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def validate_config(self) -> bool:
        """Validate configuration file.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            config_data = self.load_config()
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}") from e

        # Validate generation section if present
        if "generation" in config_data:
            generation = config_data["generation"]

            # Validate scene_type
            if "scene_type" in generation:
                valid_scene_types = ["single_pallet", "warehouse"]
                if generation["scene_type"] not in valid_scene_types:
                    raise ValueError(
                        f"Invalid scene_type. Must be one of: {valid_scene_types}"
                    )

            # Validate num_frames
            if "num_frames" in generation and (
                not isinstance(generation["num_frames"], int)
                or generation["num_frames"] <= 0
            ):
                raise ValueError("num_frames must be a positive integer")

            # Validate resolution
            if "resolution" in generation:
                resolution = generation["resolution"]
                if (
                    not isinstance(resolution, list)
                    or len(resolution) != 2
                    or not all(isinstance(x, int) and x > 0 for x in resolution)
                ):
                    raise ValueError(
                        "resolution must be a list of two positive integers [width, height]"
                    )

            # Validate export_formats
            if "export_formats" in generation:
                valid_formats = ["yolo", "coco", "voc"]
                formats = generation["export_formats"]
                if not isinstance(formats, list):
                    raise ValueError("export_formats must be a list")
                for fmt in formats:
                    if fmt not in valid_formats:
                        raise ValueError(
                            f"Invalid export format '{fmt}'. Must be one of: {valid_formats}"
                        )

            # Validate ratios
            if "train_ratio" in generation:
                ratio = generation["train_ratio"]
                if not isinstance(ratio, (int, float)) or not (0 < ratio < 1):
                    raise ValueError("train_ratio must be a number between 0 and 1")

            if "val_ratio" in generation:
                ratio = generation["val_ratio"]
                if not isinstance(ratio, (int, float)) or not (0 < ratio < 1):
                    raise ValueError("val_ratio must be a number between 0 and 1")

            # Validate that train_ratio + val_ratio < 1
            train_ratio = generation.get("train_ratio", 0.7)
            val_ratio = generation.get("val_ratio", 0.2)
            if train_ratio + val_ratio >= 1:
                raise ValueError("train_ratio + val_ratio must be less than 1")

            # Validate box_count_range
            if "box_count_range" in generation:
                box_range = generation["box_count_range"]
                if (
                    not isinstance(box_range, list)
                    or len(box_range) != 2
                    or not all(isinstance(x, int) and x > 0 for x in box_range)
                    or box_range[0] > box_range[1]
                ):
                    raise ValueError(
                        "box_count_range must be a list of two positive integers [min, max] where min <= max"
                    )

        return True

    @classmethod
    def create_example_config(cls, output_path: str) -> None:
        """Create an example configuration file.

        Args:
            output_path: Path where to save the example configuration
        """
        example_config = {
            "generation": {
                "scene_type": "single_pallet",
                "num_frames": 100,
                "batch_size": 100,
                "num_batches": 1,
                "resolution": [1280, 720],
                "output_dir": "./output",
                "export_formats": ["yolo", "coco"],
                "random_seed": 42,
                "use_gpu": True,
                "samples": 128,
                "pallet_count": 1,
                "box_count_range": [5, 15],
                "train_ratio": 0.7,
                "val_ratio": 0.2,
            },
            "project": {
                "clone_to_desktop": False,
                "desktop_path": "auto",  # Auto-detect or specify custom path
                "name": "PalletDataGenerator",
            },
            "rendering": {
                "engine": "CYCLES",
                "device": "GPU",
                "max_bounces": 4,
                "use_denoising": True,
                "denoiser": "AUTO",
                "fast_mode": False,
            },
            "scene": {
                "lighting": {
                    "hdri_path": None,
                    "sun_energy": 3.0,
                    "sun_angle": [45, 135],
                },
                "camera": {
                    "height_range": [1.4, 2.0],  # Forklift height simulation
                    "angle_range": [-30, 30],
                    "distance_range": [3.0, 8.0],
                    "focal_length": 35.0,
                    "sensor_size": 36.0,
                },
                "backgrounds": {
                    "use_random_backgrounds": False,
                    "images_dir": None,
                    "supported_formats": [".jpg", ".jpeg", ".png", ".exr", ".hdr"],
                },
                "materials": {
                    "randomize_colors": True,
                    "use_textures": True,
                    "texture_dir": None,
                },
            },
            "objects": {
                "pallet": {"dimensions": [1.2, 0.8, 0.15], "material_variations": 3},
                "boxes": {
                    "size_variations": [
                        [0.2, 0.2, 0.2],
                        [0.4, 0.3, 0.25],
                        [0.35, 0.35, 0.3],
                    ],
                    "material_variations": 5,
                    "stacking_probability": 0.7,
                },
            },
            "advanced": {
                "analysis_images": False,
                "depth_maps": False,
                "normal_maps": False,
                "segmentation_masks": False,
                "multi_pass_rendering": False,
            },
        }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            yaml.dump(example_config, f, default_flow_style=False, indent=2)
