#!/usr/bin/env python3
"""
Simplified CLI for the Unified Pallet Data Generator.
Only includes essential arguments as requested.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Check if we're running in Blender
try:
    import bpy

    RUNNING_IN_BLENDER = True
except ImportError:
    RUNNING_IN_BLENDER = False
    bpy = None

from .generator import PalletDataGenerator


def find_blender_executable():
    """Find Blender executable on the system (Windows, Linux, macOS)."""
    import glob
    import platform

    system = platform.system().lower()

    # Common Blender executable names
    if system == "windows":
        executable_names = ["blender.exe"]
        # Windows common installation paths
        common_paths = [
            "C:\\Program Files\\Blender Foundation\\Blender*\\blender.exe",
            "C:\\Program Files (x86)\\Blender Foundation\\Blender*\\blender.exe",
            "C:\\Users\\*\\AppData\\Local\\Programs\\Blender Foundation\\Blender*\\blender.exe",
            "%PROGRAMFILES%\\Blender Foundation\\Blender*\\blender.exe",
            "%PROGRAMFILES(X86)%\\Blender Foundation\\Blender*\\blender.exe",
        ]
    elif system == "darwin":  # macOS
        executable_names = ["blender", "Blender"]
        # macOS common installation paths
        common_paths = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            "/Applications/blender.app/Contents/MacOS/blender",
            "/usr/local/bin/blender",
            "/opt/homebrew/bin/blender",  # Apple Silicon Homebrew
            "/usr/local/Cellar/blender/*/bin/blender",  # Intel Homebrew
            "~/Applications/Blender.app/Contents/MacOS/Blender",
        ]
    else:  # Linux and other Unix-like systems
        executable_names = ["blender"]
        # Linux common installation paths
        common_paths = [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/opt/blender*/blender",
            "/snap/bin/blender",  # Snap package
            "/var/lib/flatpak/exports/bin/org.blender.Blender",  # Flatpak
            "~/.local/bin/blender",
            "/usr/share/blender*/blender",
        ]

    print(f"[INFO] Searching for Blender on {system.title()}...")

    # Method 1: Try to find blender in PATH
    for name in executable_names:
        blender_path = shutil.which(name)
        if blender_path and Path(blender_path).exists():
            return blender_path

    # Method 2: Try common installation paths
    for path_pattern in common_paths:
        # Expand environment variables and user home
        expanded_path = os.path.expandvars(os.path.expanduser(path_pattern))

        if "*" in expanded_path:
            # Handle wildcards for version directories
            try:
                matches = glob.glob(expanded_path)
                for match in sorted(matches, reverse=True):  # Get latest version first
                    if Path(match).exists() and Path(match).is_file():
                        print(f"[SUCCESS] Found Blender: {match}")
                        return match
            except Exception:
                continue
        else:
            path = Path(expanded_path)
            if path.exists() and path.is_file():
                print(f"[SUCCESS] Found Blender: {path}")
                return str(path)

    # Method 3: Try some additional system-specific searches
    if system == "windows":
        # Check Windows Registry (if available)
        try:
            import winreg

            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlenderFoundation\Blender"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\BlenderFoundation\Blender"),
            ]

            for hkey, subkey in registry_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        install_dir = winreg.QueryValueEx(key, "InstallDir")[0]
                        blender_exe = Path(install_dir) / "blender.exe"
                        if blender_exe.exists():
                            print(f"[SUCCESS] Found Blender via registry: {blender_exe}")
                            return str(blender_exe)
                except (FileNotFoundError, OSError):
                    continue
        except ImportError:
            pass  # winreg not available

    elif system == "linux":
        # Check for AppImage files
        appimage_locations = [
            "~/Downloads/Blender*.AppImage",
            "~/Applications/Blender*.AppImage",
            "/opt/*/Blender*.AppImage",
        ]

        for pattern in appimage_locations:
            expanded = os.path.expanduser(pattern)
            matches = glob.glob(expanded)
            for match in sorted(matches, reverse=True):
                if Path(match).exists() and os.access(match, os.X_OK):
                    print(f"[SUCCESS] Found Blender AppImage: {match}")
                    return match

    # Method 4: Try to find using 'locate' command on Unix systems
    if system != "windows":
        try:
            result = subprocess.run(
                ["locate", "blender"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.endswith("/blender") or line.endswith("/Blender"):
                        path = Path(line)
                        if (
                            path.exists()
                            and path.is_file()
                            and os.access(path, os.X_OK)
                        ):
                            print(f"[SUCCESS] Found Blender via locate: {path}")
                            return str(path)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # locate command not available or timed out

    print("[ERROR] Blender executable not found!")
    print("[INFO] Installation suggestions:")
    if system == "windows":
        print("   [UNK] Download from https://www.blender.org/download/")
        print("   [UNK] Or install via Chocolatey: choco install blender")
        print("   [UNK] Or install via Winget: winget install BlenderFoundation.Blender")
    elif system == "darwin":
        print("   [UNK] Download from https://www.blender.org/download/")
        print("   [UNK] Or install via Homebrew: brew install --cask blender")
        print("   [UNK] Or install from Mac App Store")
    else:  # Linux
        print("   [UNK] Download from https://www.blender.org/download/")
        print("   [UNK] Or install via package manager:")
        print("     - Ubuntu/Debian: sudo apt install blender")
        print("     - Fedora: sudo dnf install blender")
        print("     - Arch: sudo pacman -S blender")
        print("     - Snap: sudo snap install blender --classic")
        print("     - Flatpak: flatpak install flathub org.blender.Blender")

    return None


def run_in_blender(
    scene_path,
    mode,
    frames,
    resolution,
    output,
    debug=False,
    stacked_pallets=None,
    stacked_pallets_max=None,
    pallet_stack_vertical=None,
    pallet_stack_gap=None,
    debug_3d=False,
):
    """Execute the generator within Blender.

    This helper will embed optional pallet-stacking overrides into the temporary
    script so they are applied inside Blender.
    """
    blender_exe = find_blender_executable()
    if not blender_exe:
        print("[ERROR] Error: Blender executable not found!")
        print("[INFO] Please ensure Blender is installed and accessible in PATH")
        print("   Or install Blender from: https://www.blender.org/download/")
        sys.exit(1)

    print(f"[UNK] Found Blender: {blender_exe}")
    print("[INFO] Launching Blender to run generation...")

    # Get the actual source directory path to inject into the script
    src_dir = Path(__file__).parent.parent  # src/ directory

    # Create a temporary script that will run inside Blender
    # NOTE: use a normal string (not f-string) so placeholders like
    # {config_overrides} are not interpolated here [UNK] we replace them later.
    script_content = """
import sys
from pathlib import Path

# Add package to path
src_dir = Path("{src_dir}")
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from palletdatagenerator.generator import PalletDataGenerator
from palletdatagenerator.utils import setup_logging

try:
    # Setup logging based on debug flag
    log_level = "DEBUG" if {debug} else "INFO"
    setup_logging(level=log_level, log_file="output.log")

    # Create generator
    generator = PalletDataGenerator(mode="{mode}")

    # Config overrides supplied by the CLI runner
    config_overrides = {config_overrides}

    # Generate dataset (all parameters are passed to generate method)
    result = generator.generate(
        scene_path=Path("{scene_path}"),
        num_frames={frames},
        output_dir={output_dir},
        resolution={resolution},
        config_overrides=config_overrides,
    )

    print("[SUCCESS] Generation completed successfully!")
    print(f"   Output: {{result.get('output_path', 'Unknown')}}")
    print(f"   Frames: {{result.get('frames', 'Unknown')}}")
    print(f"   Mode: {{result.get('mode', 'Unknown')}}")

except Exception as e:
    print(f"[ERROR] Error during generation: {{e}}")
    import traceback
    traceback.print_exc()
"""

    # Write script to temporary file
    script_path = Path.cwd() / "temp_blender_script.py"
    with open(script_path, "w") as f:
        # Use string replacement instead of format to avoid KeyError issues
        formatted_script = script_content

        # Replace all template variables
        formatted_script = formatted_script.replace("{debug}", str(debug))
        formatted_script = formatted_script.replace("{mode}", mode)
        formatted_script = formatted_script.replace("{scene_path}", str(scene_path))
        formatted_script = formatted_script.replace("{frames}", str(frames))
        formatted_script = formatted_script.replace(
            "{output}", str(output) if output else "None"
        )
        formatted_script = formatted_script.replace("{resolution}", str(resolution))
        # Build config_overrides literal based on provided function args
        overrides = {}
        if stacked_pallets is not None:
            overrides["stacked_pallets_probability"] = float(stacked_pallets)
        if stacked_pallets_max is not None:
            overrides["stacked_pallets_max"] = int(stacked_pallets_max)
        if pallet_stack_vertical is not None:
            overrides["pallet_stack_vertical"] = bool(pallet_stack_vertical)
        if pallet_stack_gap is not None:
            overrides["pallet_stack_gap"] = float(pallet_stack_gap)
        if debug_3d:
            overrides["generate_debug_3d"] = True

        formatted_script = formatted_script.replace(
            "{config_overrides}", repr(overrides)
        )

        # Inject the actual source directory path
        formatted_script = formatted_script.replace("{src_dir}", str(src_dir))

        # Fix the output_dir placeholder
        if output:
            formatted_script = formatted_script.replace(
                "{output_dir}", f'Path("{output}")'
            )
        else:
            formatted_script = formatted_script.replace("{output_dir}", "None")

        f.write(formatted_script)

    try:
        # Run Blender in background with our script
        cmd = [
            blender_exe,
            str(scene_path),  # Load the scene file
            "--background",  # Run without UI
            "--python",
            str(script_path),  # Run our script
        ]

        print(f"[UNK] Executing: {' '.join(cmd)}")

        # Run Blender with output filtering
        import re

        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=0,  # Unbuffered for real-time output
        )

        frame_pattern = re.compile(r"Fra:(\d+)")
        current_frame = None

        # Filter and display relevant output in real-time
        for line in iter(process.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue

            # FIRST: Show important messages immediately (before skip filtering)
            if any(
                important in line
                for important in [
                    "[DEBUG]",
                    "[SUCCESS]",
                    "[ERROR]",
                    "[WARN]",
                    "[INFO]",
                    "[INFO]",
                    "[INFO]",
                    "Error",
                    "error",
                    "Saved:",
                    "Analysis",
                    "YOLO",
                    "COCO",
                    "VOC",
                    "blender",
                    "PIL",
                    "generation",
                    "[INFO]",
                    "[INFO]",
                    "[UNK]",
                    "[UNK]",
                    "save_frame",
                    "SCENE",
                    "warehouse",
                    "Rendering frame",
                    "TRACEBACK",
                    "Traceback",
                    'File "',
                    "IndexError",
                    "===",
                ]
            ):
                print(line)
                sys.stdout.flush()  # Force immediate output
                continue

            # THEN: Skip verbose Blender memory and timing lines
            if any(
                skip_pattern in line
                for skip_pattern in [
                    "Fra:",
                    "Mem:",
                    "Peak:",
                    "Time:",
                    "Scene, View Layer",
                    "Updating",
                    "Loading",
                    "Synchronizing",
                    "Building",
                    "Copying",
                    "Computing",
                    "Writing",
                    "Elapsed",
                    "Remaining",
                ]
            ):
                # Only show frame progress for single_pallet mode
                # (warehouse mode has its own progress messages)
                if "Fra:" in line and current_frame is not None:
                    frame_match = frame_pattern.search(line)
                    if frame_match:
                        new_frame = int(frame_match.group(1))
                        if new_frame != current_frame:
                            current_frame = new_frame
                            # Only show this for single pallet mode
                            # Warehouse mode shows its own "[UNK] Rendering frame" messages
                continue

        # Wait for process to complete
        return_code = process.wait()

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)

        print("[SUCCESS] Blender execution completed!")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Blender execution failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    except KeyboardInterrupt:
        print("\n[WARN]  Generation interrupted by user")
        sys.exit(1)

    finally:
        # Clean up temporary script
        if script_path.exists():
            script_path.unlink()


def create_parser():
    """Create argument parser with only essential arguments."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic pallet datasets with Blender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate single pallet dataset (default mode)
  palletgen scenes/one_pallet.blend --frames 100

  # Generate warehouse dataset
  palletgen scenes/warehouse_objects.blend --mode warehouse --frames 200 --resolution 1920 1080
        """,
    )

    # Scene path (required)
    parser.add_argument(
        "scene_path", type=Path, help="Path to Blender scene file (.blend)"
    )

    # Mode selection (optional, defaults to single_pallet)
    parser.add_argument(
        "--mode",
        "-m",
        choices=["single_pallet", "warehouse"],
        default="single_pallet",
        help="Generation mode: single_pallet (default) or warehouse",
    )

    # Essential arguments only
    parser.add_argument(
        "--frames",
        "-f",
        type=int,
        default=50,
        help="Number of frames to generate (default: 50)",
    )

    parser.add_argument(
        "--resolution",
        "-r",
        nargs=2,
        type=int,
        metavar=("WIDTH", "HEIGHT"),
        default=[1024, 768],
        help="Image resolution (default: 1024 768)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory (default: output/{mode}/generated_XXXXXX)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging for detailed output",
    )

    # Pallet stacking overrides (optional)
    parser.add_argument(
        "--stacked-pallets",
        dest="stacked_pallets",
        type=float,
        default=None,
        help="Probability (0..1) to create a stacked pallet scene (float, default: disabled)",
    )
    parser.add_argument(
        "--stacked-pallets-max",
        dest="stacked_pallets_max",
        type=int,
        default=5,
        help="Maximum number of pallets to stack when stacking is triggered (int, default: 5)",
    )
    parser.add_argument(
        "--pallet-stack-vertical",
        dest="pallet_stack_vertical",
        action="store_true",
        default=True,
        help="Stack duplicates vertically (default behavior)",
    )
    parser.add_argument(
        "--no-pallet-stack-vertical",
        dest="pallet_stack_vertical",
        action="store_false",
        help="Do not stack duplicates vertically; offset in X/Y instead",
    )
    parser.add_argument(
        "--pallet-stack-gap",
        dest="pallet_stack_gap",
        type=float,
        default=0.0,
        help="Vertical gap between stacked pallets (float, Blender units, default: 0.0)",
    )
    parser.add_argument(
        "--debug-3d",
        dest="debug_3d",
        action="store_true",
        default=False,
        help="Generate debug_3d folder with 3D visualizations (default: False)",
    )

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging based on debug flag
    from .utils import setup_logging

    log_level = "DEBUG" if args.debug else "INFO"
    setup_logging(level=log_level, log_file="output.log")

    # Validate scene file
    if not args.scene_path.exists():
        print(f"[ERROR] Error: Scene file not found: {args.scene_path}")
        sys.exit(1)

    if args.scene_path.suffix != ".blend":
        print(f"[ERROR] Error: Scene file must be a .blend file: {args.scene_path}")
        sys.exit(1)

    print("[INFO] Starting Pallet Data Generator")
    print(f"   Mode: {args.mode}")
    print(f"   Scene: {args.scene_path}")
    print(f"   Frames: {args.frames}")
    print(f"   Resolution: {args.resolution[0]}x{args.resolution[1]}")
    if args.debug:
        print("   Debug: Enabled")

    # Check if we're running inside Blender or outside
    if not RUNNING_IN_BLENDER:
        print("[UNK] Not running in Blender - launching Blender automatically...")
        run_in_blender(
            scene_path=args.scene_path,
            mode=args.mode,
            frames=args.frames,
            resolution=args.resolution,
            output=args.output,
            debug=args.debug,
            stacked_pallets=args.stacked_pallets,
            stacked_pallets_max=args.stacked_pallets_max,
            pallet_stack_vertical=args.pallet_stack_vertical,
            pallet_stack_gap=args.pallet_stack_gap,
            debug_3d=args.debug_3d,
        )
        return

    # If we're here, we're running inside Blender
    try:
        # Create generator
        generator = PalletDataGenerator(mode=args.mode)

        # Build config_overrides from CLI args (only include set values)
        config_overrides = {}
        if hasattr(args, "stacked_pallets") and args.stacked_pallets is not None:
            # Probability 0..1 to create a stacked pallet scene
            config_overrides["stacked_pallets_probability"] = float(
                args.stacked_pallets
            )
        if (
            hasattr(args, "stacked_pallets_max")
            and args.stacked_pallets_max is not None
        ):
            # Maximum number of pallets to stack (driver for random choice)
            config_overrides["stacked_pallets_max"] = int(args.stacked_pallets_max)
        if (
            hasattr(args, "pallet_stack_vertical")
            and args.pallet_stack_vertical is not None
        ):
            config_overrides["pallet_stack_vertical"] = bool(args.pallet_stack_vertical)
        if hasattr(args, "pallet_stack_gap") and args.pallet_stack_gap is not None:
            config_overrides["pallet_stack_gap"] = float(args.pallet_stack_gap)
        if hasattr(args, "debug_3d") and args.debug_3d:
            config_overrides["generate_debug_3d"] = True

        # Generate dataset (all parameters are passed to generate method)
        result = generator.generate(
            scene_path=args.scene_path,
            num_frames=args.frames,
            output_dir=args.output,
            resolution=args.resolution,
            config_overrides=config_overrides if config_overrides else None,
        )

        print("[SUCCESS] Generation completed successfully!")
        print(f"   Output: {result['output_path']}")
        print(f"   Frames: {result['frames']}")
        print(f"   Mode: {result['mode']}")

        if "pallets_detected" in result:
            print(f"   Pallets detected: {result['pallets_detected']}")

    except KeyboardInterrupt:
        print("\n[WARN]  Generation interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Error during generation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
