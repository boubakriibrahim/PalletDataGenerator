"""Argument parser module for PalletDataGenerator CLI.

This module handles command-line argument parsing with priority over config files.
Args have higher priority than config file settings.
"""

import argparse
import platform
from pathlib import Path
from typing import Any


def get_desktop_path() -> str:
    """Auto-detect desktop directory based on OS.

    Returns:
        Path to desktop directory
    """
    system = platform.system()
    home = Path.home()

    if system in ("Darwin", "Windows"):  # macOS or Windows
        return str(home / "Desktop")
    elif system == "Linux":
        # Try common Linux desktop paths
        desktop_paths = [
            home / "Desktop",
            home / "Bureau",  # French
            home / "Escritorio",  # Spanish
            home / "Área de Trabalho",  # Portuguese
        ]
        for path in desktop_paths:
            if path.exists():
                return str(path)
        return str(home / "Desktop")  # Default fallback
    else:
        return str(home / "Desktop")


def create_parser() -> argparse.ArgumentParser:
    """Create comprehensive argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="PalletDataGenerator - Generate synthetic datasets using Blender",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  # Basic generation
  python -m palletdatagenerator generate --output ./dataset --num-frames 100

  # Use config file with CLI overrides
  python -m palletdatagenerator generate --config config.yaml --output ./custom_output

  # Warehouse scene with multiple formats
  python -m palletdatagenerator generate --scene-type warehouse --export-format yolo coco voc

  # With Blender (recommended)
  blender warehouse_objects.blend --python -m palletdatagenerator.blender_runner -- generate --output ./dataset
        """,
    )

    # Main subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === INFO COMMAND ===
    info_parser = subparsers.add_parser(
        "info",
        help="Show system and version information",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    info_parser.add_argument(
        "--version", action="store_true", help="Show version information only"
    )
    info_parser.add_argument(
        "--system-info", action="store_true", help="Show detailed system information"
    )

    # === CONFIG COMMAND ===
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration file management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_action", help="Config actions"
    )

    # Create sample config
    create_parser = config_subparsers.add_parser(
        "create", help="Create sample configuration file"
    )
    create_parser.add_argument(
        "output_path", help="Path for the new configuration file"
    )

    # Validate config
    validate_parser = config_subparsers.add_parser(
        "validate", help="Validate configuration file"
    )
    validate_parser.add_argument(
        "config_path", help="Path to configuration file to validate"
    )

    # === GENERATE COMMAND ===
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate synthetic dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Configuration
    gen_parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to YAML configuration file (CLI args override config values)",
    )

    # Basic settings
    gen_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory for generated dataset (auto-creates batch folders: generated_XXXX)",
    )

    gen_parser.add_argument(
        "--scene-type",
        choices=["single_pallet", "warehouse"],
        default="single_pallet",
        help="Type of scene to generate",
    )

    gen_parser.add_argument(
        "--num-frames",
        type=int,
        default=100,
        help="Number of frames to generate per batch",
    )

    gen_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of frames per batch (creates separate folders)",
    )

    gen_parser.add_argument(
        "--num-batches", type=int, default=1, help="Number of batches to generate"
    )

    # Image settings
    gen_parser.add_argument(
        "--resolution",
        type=int,
        nargs=2,
        default=[1280, 720],
        metavar=("WIDTH", "HEIGHT"),
        help="Image resolution (width height)",
    )

    gen_parser.add_argument(
        "--export-format",
        choices=["yolo", "coco", "voc"],
        action="append",
        help="Annotation export format(s). Can be specified multiple times.",
    )

    # Randomization
    gen_parser.add_argument(
        "--random-seed", type=int, help="Random seed for reproducible generation"
    )

    gen_parser.add_argument(
        "--background-images-dir",
        type=str,
        help="Directory containing background images to use randomly",
    )

    gen_parser.add_argument(
        "--use-random-backgrounds",
        action="store_true",
        help="Enable random background images from background-images-dir",
    )

    # Rendering options
    gen_parser.add_argument(
        "--gpu", action="store_true", help="Use GPU for rendering (if available)"
    )

    gen_parser.add_argument(
        "--samples",
        type=int,
        default=128,
        help="Number of samples for rendering quality (32=fast, 128=quality, 256=high)",
    )

    gen_parser.add_argument(
        "--engine",
        choices=["CYCLES", "EEVEE"],
        default="CYCLES",
        help="Blender rendering engine",
    )

    gen_parser.add_argument(
        "--denoiser",
        choices=["AUTO", "OPTIX", "OPENIMAGE"],
        default="AUTO",
        help="Denoising method for cleaner renders",
    )

    # Scene parameters
    gen_parser.add_argument(
        "--pallet-count",
        type=int,
        default=1,
        help="Number of pallets in warehouse scenes",
    )

    gen_parser.add_argument(
        "--box-count-range",
        type=int,
        nargs=2,
        default=[5, 15],
        metavar=("MIN", "MAX"),
        help="Range for number of boxes per pallet",
    )

    gen_parser.add_argument(
        "--camera-height-range",
        type=float,
        nargs=2,
        default=[1.4, 2.0],
        metavar=("MIN", "MAX"),
        help="Camera height range in meters (forklift simulation)",
    )

    # Dataset splitting
    gen_parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Ratio of data for training split",
    )

    gen_parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Ratio of data for validation split",
    )

    # Project setup
    gen_parser.add_argument(
        "--clone-to-desktop",
        action="store_true",
        help=f"Clone/copy project to desktop directory ({get_desktop_path()})",
    )

    gen_parser.add_argument(
        "--desktop-path",
        type=str,
        default=get_desktop_path(),
        help="Custom desktop path (auto-detected by default)",
    )

    # Advanced options
    gen_parser.add_argument(
        "--fast-mode",
        action="store_true",
        help="Enable fast rendering mode (lower quality, faster generation)",
    )

    gen_parser.add_argument(
        "--analysis-images",
        action="store_true",
        help="Generate analysis images with annotations overlay",
    )

    gen_parser.add_argument(
        "--depth-maps", action="store_true", help="Generate depth maps"
    )

    gen_parser.add_argument(
        "--normal-maps", action="store_true", help="Generate normal maps"
    )

    gen_parser.add_argument(
        "--segmentation-masks", action="store_true", help="Generate segmentation masks"
    )

    # Logging
    gen_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )

    gen_parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (default: output_dir/generation.log)",
    )

    gen_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output to console"
    )

    gen_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress most output except errors"
    )

    # === SETUP COMMAND ===
    setup_parser = subparsers.add_parser("setup", help="Setup development environment")
    setup_parser.add_argument(
        "--venv-name", default="pallet_env", help="Name for virtual environment"
    )
    setup_parser.add_argument(
        "--python-version",
        default="3.11",
        help="Python version to use (recommended: 3.11 for Blender 4.5.1 LTS compatibility)",
    )
    setup_parser.add_argument(
        "--blender-version",
        default="4.5.1",
        help="Target Blender version (4.5.1 LTS recommended)",
    )

    return parser


def merge_config_and_args(
    config_data: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Merge configuration file data with command-line arguments.

    Command-line arguments have higher priority than config file values.

    Args:
        config_data: Data from configuration file
        args: Parsed command-line arguments

    Returns:
        Merged configuration dictionary
    """
    merged = config_data.copy()

    # Override config with CLI args (only non-None values)
    args_dict = vars(args)
    for key, value in args_dict.items():
        if value is not None:
            # Handle nested config structure
            if key in [
                "scene_type",
                "num_frames",
                "resolution",
                "output_dir",
                "export_formats",
                "random_seed",
                "use_gpu",
                "samples",
            ]:
                if "generation" not in merged:
                    merged["generation"] = {}
                merged["generation"][key] = value
            elif key.startswith("camera_"):
                if "scene" not in merged:
                    merged["scene"] = {}
                if "camera" not in merged["scene"]:
                    merged["scene"]["camera"] = {}
                merged["scene"]["camera"][key.replace("camera_", "")] = value
            elif key in ["background_images_dir", "use_random_backgrounds"]:
                if "scene" not in merged:
                    merged["scene"] = {}
                if "backgrounds" not in merged["scene"]:
                    merged["scene"]["backgrounds"] = {}
                merged["scene"]["backgrounds"][key.replace("background_", "")] = value
            elif key in ["clone_to_desktop", "desktop_path"]:
                if "project" not in merged:
                    merged["project"] = {}
                merged["project"][key] = value
            else:
                merged[key] = value

    return merged


def validate_args(args: argparse.Namespace) -> bool:
    """Validate command-line arguments.

    Args:
        args: Parsed arguments

    Returns:
        True if arguments are valid
    """
    if args.command == "generate":
        # Validate resolution
        if args.resolution and (args.resolution[0] <= 0 or args.resolution[1] <= 0):
            print("❌ Error: Resolution must be positive integers")
            return False

        # Validate frame counts
        if args.num_frames and args.num_frames <= 0:
            print("❌ Error: Number of frames must be positive")
            return False

        if args.batch_size and args.batch_size <= 0:
            print("❌ Error: Batch size must be positive")
            return False

        if args.num_batches and args.num_batches <= 0:
            print("❌ Error: Number of batches must be positive")
            return False

        # Validate ratios
        if args.train_ratio and not (0 < args.train_ratio < 1):
            print("❌ Error: Train ratio must be between 0 and 1")
            return False

        if args.val_ratio and not (0 < args.val_ratio < 1):
            print("❌ Error: Validation ratio must be between 0 and 1")
            return False

        if (
            args.train_ratio
            and args.val_ratio
            and args.train_ratio + args.val_ratio >= 1
        ):
            print("❌ Error: Train + validation ratios must be less than 1")
            return False

        # Validate box count range
        if args.box_count_range and args.box_count_range[0] > args.box_count_range[1]:
            print("❌ Error: Box count minimum cannot be greater than maximum")
            return False

        # Validate camera height range
        if (
            args.camera_height_range
            and args.camera_height_range[0] > args.camera_height_range[1]
        ):
            print("❌ Error: Camera height minimum cannot be greater than maximum")
            return False

        # Validate background images directory
        if args.background_images_dir:
            bg_path = Path(args.background_images_dir)
            if not bg_path.exists():
                print(
                    f"❌ Error: Background images directory not found: {args.background_images_dir}"
                )
                return False
            if not bg_path.is_dir():
                print(
                    f"❌ Error: Background images path is not a directory: {args.background_images_dir}"
                )
                return False

        # Set default export format if none specified
        if not args.export_format:
            args.export_format = ["yolo"]

        # Handle quiet/verbose conflict
        if args.quiet and args.verbose:
            print("❌ Error: Cannot use both --quiet and --verbose")
            return False

    return True


def get_batch_output_dir(base_output_dir: str, batch_number: int) -> str:
    """Generate batch output directory name.

    Args:
        base_output_dir: Base output directory
        batch_number: Batch number (1-based)

    Returns:
        Path to batch output directory
    """
    batch_name = f"generated_{batch_number:04d}"
    return str(Path(base_output_dir) / batch_name)


def show_compatibility_info():
    """Show version compatibility information."""
    print(
        """
🐍 Python & Blender Compatibility Information
============================================

📍 RECOMMENDED VERSIONS (Tested & Optimized):
  • Python: 3.11.13
  • Blender: 4.5.1 LTS

✅ SUPPORTED VERSIONS:
  • Python: 3.11 (3.11 recommended)
  • Blender: 4.5 (4.5.2 LTS recommended)

⚡ PERFORMANCE NOTES:
  • Python 3.11.13 provides best performance with Blender 4.5.1 LTS
  • Newer versions should work but may have minor compatibility issues
  • Blender 4.5.2 LTS offers stable API and long-term support

🔧 GPU ACCELERATION:
  • NVIDIA GPUs: CUDA support recommended
  • AMD GPUs: OpenCL support
  • Apple Silicon: Metal performance shaders
    """
    )


if __name__ == "__main__":
    # Test argument parser
    parser = create_parser()

    # Test with sample arguments
    test_args = [
        "generate",
        "--output",
        "./test_output",
        "--num-frames",
        "50",
        "--scene-type",
        "warehouse",
        "--export-format",
        "yolo",
        "coco",
        "--gpu",
        "--verbose",
    ]

    args = parser.parse_args(test_args)
    print("✅ Parser test successful!")
    print(f"Command: {args.command}")
    print(f"Output: {args.output}")
    print(f"Frames: {args.num_frames}")
    print(f"GPU: {args.gpu}")
