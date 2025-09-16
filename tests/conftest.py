"""Test configuration and shared fixtures for the test suite."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_blender():
    """Mock Blender modules that aren't available in testing environment."""
    mock_bpy = Mock()
    mock_mathutils = Mock()

    # Mock common bpy operations
    mock_bpy.context.scene.render.resolution_x = 1024
    mock_bpy.context.scene.render.resolution_y = 768
    mock_bpy.context.scene.render.filepath = "/tmp/test"
    mock_bpy.ops.render.render = Mock()
    mock_bpy.data.objects = {}
    mock_bpy.data.materials = {}
    mock_bpy.data.lights = {}

    # Mock mathutils
    mock_mathutils.Vector = Mock(return_value=Mock())
    mock_mathutils.Matrix = Mock()

    with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
        yield mock_bpy, mock_mathutils


@pytest.fixture
def sample_scene_file(temp_dir: Path) -> Path:
    """Create a mock Blender scene file for testing."""
    scene_file = temp_dir / "test_scene.blend"
    # Create a dummy file to simulate a Blender scene
    scene_file.write_bytes(b"BLENDER test scene data")
    return scene_file


@pytest.fixture
def sample_config() -> dict:
    """Provide a sample configuration for testing."""
    return {
        "num_images": 5,
        "resolution_x": 1024,
        "resolution_y": 768,
        "render_engine": "CYCLES",
        "output_formats": ["yolo", "coco"],
        "use_gpu": False,
    }
