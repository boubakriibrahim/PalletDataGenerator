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

    print(f"🔍 Searching for Blender on {system.title()}...")

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
                        print(f"✅ Found Blender: {match}")
                        return match
            except Exception:
                continue
        else:
            path = Path(expanded_path)
            if path.exists() and path.is_file():
                print(f"✅ Found Blender: {path}")
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
                            print(f"✅ Found Blender via registry: {blender_exe}")
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
                    print(f"✅ Found Blender AppImage: {match}")
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
                            print(f"✅ Found Blender via locate: {path}")
                            return str(path)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # locate command not available or timed out

    print("❌ Blender executable not found!")
    print("💡 Installation suggestions:")
    if system == "windows":
        print("   • Download from https://www.blender.org/download/")
        print("   • Or install via Chocolatey: choco install blender")
        print("   • Or install via Winget: winget install BlenderFoundation.Blender")
    elif system == "darwin":
        print("   • Download from https://www.blender.org/download/")
        print("   • Or install via Homebrew: brew install --cask blender")
        print("   • Or install from Mac App Store")
    else:  # Linux
        print("   • Download from https://www.blender.org/download/")
        print("   • Or install via package manager:")
        print("     - Ubuntu/Debian: sudo apt install blender")
        print("     - Fedora: sudo dnf install blender")
        print("     - Arch: sudo pacman -S blender")
        print("     - Snap: sudo snap install blender --classic")
        print("     - Flatpak: flatpak install flathub org.blender.Blender")

    return None


def run_in_blender(scene_path, mode, frames, resolution, output, debug=False):
    """Execute the generator within Blender."""
    blender_exe = find_blender_executable()
    if not blender_exe:
        print("❌ Error: Blender executable not found!")
        print("💡 Please ensure Blender is installed and accessible in PATH")
        print("   Or install Blender from: https://www.blender.org/download/")
        sys.exit(1)

    print(f"🎬 Found Blender: {blender_exe}")
    print("🚀 Launching Blender to run generation...")

    # Create a temporary script that will run inside Blender
    script_content = f"""
import sys
from pathlib import Path

# Add package to path
package_dir = Path("{Path(__file__).parent}")
if str(package_dir.parent) not in sys.path:
    sys.path.insert(0, str(package_dir.parent))

from palletdatagenerator.generator import PalletDataGenerator
from palletdatagenerator.utils import setup_logging

try:
    # Setup logging based on debug flag
    log_level = "DEBUG" if {debug} else "INFO"
    setup_logging(level=log_level, log_file="output.log")

    # Create generator
    generator = PalletDataGenerator(mode="{mode}")

    # Generate dataset (all parameters are passed to generate method)
    result = generator.generate(
        scene_path=Path("{scene_path}"),
        num_frames={frames},
        output_dir={f'Path("{output}")' if output else None},
        resolution={resolution}
    )

    print("✅ Generation completed successfully!")
    print(f"   Output: {{result.get('output_path', 'Unknown')}}")
    print(f"   Frames: {{result.get('frames', 'Unknown')}}")
    print(f"   Mode: {{result.get('mode', 'Unknown')}}")

except Exception as e:
    print(f"❌ Error during generation: {{e}}")
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

        # Fix the Path(__file__).parent issue
        formatted_script = formatted_script.replace(
            "{Path(__file__).parent}", "__file__"
        )

        # Fix the f-string issue for output
        if output:
            formatted_script = formatted_script.replace(
                "{f'Path(\"{output}\")' if output else None}", f'Path("{output}")'
            )
        else:
            formatted_script = formatted_script.replace(
                "{f'Path(\"{output}\")' if output else None}", "None"
            )

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

        print(f"🎬 Executing: {' '.join(cmd)}")

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

            # Skip verbose Blender memory and timing lines
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
                            # Warehouse mode shows its own "📸 Rendering frame" messages
                continue

            # Show important messages immediately
            if any(
                important in line
                for important in [
                    "[DEBUG]",
                    "✅",
                    "❌",
                    "⚠️",
                    "📊",
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
                    "🚀",
                    "📁",
                    "📸",
                    "🏭",
                    "save_frame",
                    "SCENE",
                    "warehouse",
                    "Rendering frame",
                ]
            ):
                print(line)
                sys.stdout.flush()  # Force immediate output

        # Wait for process to complete
        return_code = process.wait()

        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)

        print("✅ Blender execution completed!")

    except subprocess.CalledProcessError as e:
        print(f"❌ Blender execution failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    except KeyboardInterrupt:
        print("\n⚠️  Generation interrupted by user")
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
        print(f"❌ Error: Scene file not found: {args.scene_path}")
        sys.exit(1)

    if args.scene_path.suffix != ".blend":
        print(f"❌ Error: Scene file must be a .blend file: {args.scene_path}")
        sys.exit(1)

    print("🚀 Starting Pallet Data Generator")
    print(f"   Mode: {args.mode}")
    print(f"   Scene: {args.scene_path}")
    print(f"   Frames: {args.frames}")
    print(f"   Resolution: {args.resolution[0]}x{args.resolution[1]}")
    if args.debug:
        print("   Debug: Enabled")

    # Check if we're running inside Blender or outside
    if not RUNNING_IN_BLENDER:
        print("🎬 Not running in Blender - launching Blender automatically...")
        run_in_blender(
            scene_path=args.scene_path,
            mode=args.mode,
            frames=args.frames,
            resolution=args.resolution,
            output=args.output,
            debug=args.debug,
        )
        return

    # If we're here, we're running inside Blender
    try:
        # Create generator
        generator = PalletDataGenerator(mode=args.mode)

        # Generate dataset (all parameters are passed to generate method)
        result = generator.generate(
            scene_path=args.scene_path,
            num_frames=args.frames,
            output_dir=args.output,
            resolution=args.resolution,
        )

        print("✅ Generation completed successfully!")
        print(f"   Output: {result['output_path']}")
        print(f"   Frames: {result['frames']}")
        print(f"   Mode: {result['mode']}")

        if "pallets_detected" in result:
            print(f"   Pallets detected: {result['pallets_detected']}")

    except KeyboardInterrupt:
        print("\n⚠️  Generation interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Error during generation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
