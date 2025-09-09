"""Command Line Interface for PalletDataGenerator.

This module provides the main CLI entry point for the PalletDataGenerator,
allowing users to generate synthetic datasets through command-line commands.
"""

import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any

# Import our modules
from .args_parser import create_parser, get_desktop_path
from .core.config_loader import ConfigLoader
from .core.generator import GenerationConfig
from .utils import setup_logging

# Setup logging
logger = logging.getLogger(__name__)


def print_banner():
    """Print the application banner."""
    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║                   PALLETDATAGENERATOR                        ║
║               Professional Blender Dataset Library            ║
╠═══════════════════════════════════════════════════════════════╣
║  🎬 Multi-Scene Generation  │  📊 Multiple Export Formats    ║
║  ⚡ GPU-Accelerated         │  🔧 YAML Configuration         ║
║  🐍 Professional Code       │  📦 Batch Processing           ║
╚═══════════════════════════════════════════════════════════════╝
    """
    )


def check_blender_environment() -> bool:
    """Check if running inside Blender environment.

    Returns:
        True if Blender is available, False otherwise
    """
    try:
        import importlib.util

        return importlib.util.find_spec("bpy") is not None
    except ImportError:
        return False


def print_system_info():
    """Print system information."""
    print("🖥️  SYSTEM INFORMATION")
    print("=" * 50)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python: {sys.version.split()[0]} ({platform.python_implementation()})")
    print(f"Working Directory: {os.getcwd()}")

    # Check Blender availability
    if check_blender_environment():
        import bpy

        print(f"Blender: {bpy.app.version_string} ✅")
    else:
        print("Blender: Not available (run within Blender for full functionality) ⚠️")

    print()


def handle_info_command(args) -> int:
    """Handle the info command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success)
    """
    if hasattr(args, "version") and args.version:
        from . import __version__

        print(f"PalletDataGenerator v{__version__}")
        return 0

    if hasattr(args, "system_info") and args.system_info:
        print_system_info()
        return 0

    # Default info command
    print_banner()
    print_system_info()
    return 0


def handle_config_command(args) -> int:
    """Handle the config command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    if hasattr(args, "config_action"):
        if args.config_action == "create":
            return create_sample_config(args.output_path)
        elif args.config_action == "validate":
            return validate_config_file(args.config_path)

    print("❌ No config action specified. Use --help for available options.")
    return 1


def create_sample_config(config_path: str) -> int:
    """Create a sample configuration file.

    Args:
        config_path: Path where to create the config file

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        config_path = Path(config_path)

        # Create sample configuration
        sample_config = {
            "generation": {
                "scene_type": "single_pallet",
                "num_frames": 100,
                "resolution": [1280, 720],
                "output_dir": str(get_desktop_path() + "/pallet_dataset"),
                "export_formats": ["yolo", "coco"],
                "use_gpu": True,
                "samples": 128,
            },
            "rendering": {"engine": "CYCLES", "denoiser": "AUTO", "use_gpu": True},
            "camera": {"focal_mm": 35.0, "sensor_mm": 36.0, "height_range": [1.0, 3.0]},
            "lighting": {
                "randomize_per_frame": True,
                "light_count_range": [2, 4],
                "use_colored_lights": True,
            },
            "dataset": {"train_ratio": 0.7, "val_ratio": 0.2, "test_ratio": 0.1},
        }

        # Save to YAML file
        import yaml

        with open(config_path, "w") as f:
            yaml.dump(sample_config, f, default_flow_style=False, indent=2)

        print(f"✅ Sample configuration created: {config_path}")
        print("📝 Edit the file to customize your dataset generation settings.")
        return 0

    except Exception as e:
        print(f"❌ Error creating config file: {e}")
        return 1


def validate_config_file(config_path: str) -> int:
    """Validate a configuration file.

    Args:
        config_path: Path to config file to validate

    Returns:
        Exit code (0 for valid, 1 for invalid)
    """
    try:
        config_loader = ConfigLoader(config_path)
        config = config_loader.load_config()

        print(f"✅ Configuration file is valid: {config_path}")
        print(f"📊 Found {len(config)} main sections")

        # Show summary
        if "generation" in config:
            gen_config = config["generation"]
            print(f"   • Scene type: {gen_config.get('scene_type', 'single_pallet')}")
            print(f"   • Frames: {gen_config.get('num_frames', 100)}")
            print(f"   • Resolution: {gen_config.get('resolution', [1280, 720])}")
            print(f"   • Output: {gen_config.get('output_dir', './output')}")

        return 0

    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return 1


def merge_config_with_args(config_dict: dict[str, Any], args) -> dict[str, Any]:
    """Merge configuration file with command line arguments.

    Command line arguments take precedence over config file values.

    Args:
        config_dict: Configuration dictionary from file
        args: Parsed command line arguments

    Returns:
        Merged configuration dictionary
    """
    # Start with config file values
    merged_config = config_dict.copy()

    # Override with command line arguments if provided
    if hasattr(args, "output") and args.output:
        merged_config.setdefault("generation", {})["output_dir"] = args.output

    if hasattr(args, "num_frames") and args.num_frames:
        merged_config.setdefault("generation", {})["num_frames"] = args.num_frames

    if hasattr(args, "resolution") and args.resolution:
        merged_config.setdefault("generation", {})["resolution"] = args.resolution

    if hasattr(args, "scene_type") and args.scene_type:
        merged_config.setdefault("generation", {})["scene_type"] = args.scene_type

    if hasattr(args, "export_format") and args.export_format:
        merged_config.setdefault("generation", {})[
            "export_formats"
        ] = args.export_format

    if hasattr(args, "gpu") and args.gpu:
        merged_config.setdefault("generation", {})["use_gpu"] = True
        merged_config.setdefault("rendering", {})["use_gpu"] = True

    if hasattr(args, "samples") and args.samples:
        merged_config.setdefault("generation", {})["samples"] = args.samples

    if hasattr(args, "engine") and args.engine:
        merged_config.setdefault("rendering", {})["engine"] = args.engine

    return merged_config


def handle_generate_command(args) -> int:
    """Handle the generate command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        print("🚀 Starting dataset generation...")

        # Load configuration if provided
        config_dict = {}
        if hasattr(args, "config") and args.config:
            print(f"📁 Loading configuration from: {args.config}")
            config_loader = ConfigLoader(args.config)
            config_dict = config_loader.load_config()

        # Merge config with command line arguments
        merged_config = merge_config_with_args(config_dict, args)

        # Check if we're running in Blender
        if not check_blender_environment():
            print("⚠️  WARNING: Blender not detected!")
            print("💡 For full functionality, run within Blender:")
            print(
                "   blender scene.blend --python -m palletdatagenerator.cli -- generate --output ./dataset"
            )
            print("🔄 Falling back to configuration validation only...")

            # Just validate and show what would be generated
            gen_config = merged_config.get("generation", {})
            print("✅ Configuration validated successfully:")
            print(f"   • Scene: {gen_config.get('scene_type', 'single_pallet')}")
            print(f"   • Frames: {gen_config.get('num_frames', 100)}")
            print(f"   • Output: {gen_config.get('output_dir', './output')}")
            print(f"   • Formats: {gen_config.get('export_formats', ['yolo'])}")

            return 0

        # Import Blender-specific modules
        from .blender_runner import BlenderEnvironmentManager
        from .core.generator import PalletGenerator, WarehouseGenerator

        # Validate Blender environment
        env_manager = BlenderEnvironmentManager()
        if not env_manager.validate_blender_environment():
            print("❌ Blender environment validation failed!")
            print("💡 Ensure your scene has:")
            print("   • Objects named with 'pallet' prefix")
            print("   • Box template objects named 'box1', 'box2', etc.")
            return 1

        # Create generation configuration
        gen_params = merged_config.get("generation", {})
        generation_config = GenerationConfig(
            output_dir=gen_params.get("output_dir", "./output"),
            num_images=gen_params.get("num_frames", 100),
            resolution=tuple(gen_params.get("resolution", [1280, 720])),
            render_engine=merged_config.get("rendering", {}).get("engine", "CYCLES"),
            export_formats=gen_params.get("export_formats", ["yolo"]),
            camera_config=merged_config.get("camera", {}),
            lighting_config=merged_config.get("lighting", {}),
        )

        # Choose generator based on scene type
        scene_type = gen_params.get("scene_type", "single_pallet")

        if scene_type == "single_pallet":
            print("🎯 Initializing Single Pallet Generator")
            generator = PalletGenerator(generation_config)
        elif scene_type == "warehouse":
            print("🏭 Initializing Warehouse Generator")
            generator = WarehouseGenerator(generation_config)
        else:
            print(f"❌ Unknown scene type: {scene_type}")
            return 1

        # Setup GPU if requested
        if merged_config.get("rendering", {}).get("use_gpu", False):
            env_manager.setup_blender_preferences(use_gpu=True)

        # Generate dataset
        print(f"🎬 Generating {generation_config.num_images} frames...")
        generator.generate_dataset()

        print("✅ Dataset generation completed successfully!")
        print(f"📁 Output directory: {generation_config.output_dir}")

        return 0

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        if hasattr(args, "verbose") and args.verbose:
            import traceback

            traceback.print_exc()
        return 1


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Create argument parser
        parser = create_parser()

        # Parse arguments
        args = parser.parse_args()

        # Setup logging
        log_level = "DEBUG" if hasattr(args, "verbose") and args.verbose else "INFO"
        setup_logging(level=log_level)

        # Handle different commands
        if args.command == "info":
            return handle_info_command(args)
        elif args.command == "config":
            return handle_config_command(args)
        elif args.command == "generate":
            return handle_generate_command(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
