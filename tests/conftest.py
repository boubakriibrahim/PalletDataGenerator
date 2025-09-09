"""Test configuration and shared fixtures."""

import shutil
import tempfile
from unittest.mock import Mock

import pytest


# Mock Blender modules for testing
class MockVector:
    def __init__(self, *args):
        if len(args) == 1 and hasattr(args[0], "__iter__"):
            self.x, self.y, self.z = args[0][:3]
        elif len(args) >= 3:
            self.x, self.y, self.z = args[:3]
        else:
            self.x = self.y = self.z = 0.0

    def __add__(self, other):
        return MockVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return MockVector(self.x - other.x, self.y - other.y, self.z - other.z)

    def normalized(self):
        return self


class MockMatrix:
    def __init__(self, *args):
        pass


class MockEuler:
    def __init__(self, *args):
        pass


# Mock bpy modules
class MockBpy:
    class context:
        scene = Mock()
        preferences = Mock()
        evaluated_depsgraph_get = Mock()
        active_object = Mock()
        view_layer = Mock()

    class data:
        objects = []
        materials = Mock()
        collections = Mock()

    class ops:
        class render:
            @staticmethod
            def render(write_still=True):
                pass

        class object:
            @staticmethod
            def light_add(type="POINT"):
                pass

        class mesh:
            @staticmethod
            def primitive_plane_add(size=20, location=(0, 0, -1)):
                pass


@pytest.fixture(scope="session", autouse=True)
def mock_blender():
    """Mock Blender modules for testing."""
    import sys

    # Mock the Blender modules
    mock_bpy = MockBpy()
    mock_mathutils = Mock()
    mock_mathutils.Vector = MockVector
    mock_mathutils.Matrix = MockMatrix
    mock_mathutils.Euler = MockEuler

    mock_bpy_extras = Mock()
    mock_bpy_extras.object_utils.world_to_camera_view = Mock(
        return_value=MockVector(0.5, 0.5, 1.0)
    )

    sys.modules["bpy"] = mock_bpy
    sys.modules["mathutils"] = mock_mathutils
    sys.modules["bpy_extras"] = mock_bpy_extras
    sys.modules["bpy_extras.object_utils"] = mock_bpy_extras.object_utils

    yield mock_bpy

    # Cleanup
    for module in ["bpy", "mathutils", "bpy_extras", "bpy_extras.object_utils"]:
        if module in sys.modules:
            del sys.modules[module]


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_generation_config(temp_output_dir):
    """Create a sample generation configuration for testing."""
    from palletdatagenerator.core.generator import GenerationConfig

    return GenerationConfig(
        output_dir=temp_output_dir,
        num_images=5,
        resolution=(640, 480),
        export_formats=["yolo", "coco"],
    )


@pytest.fixture
def sample_detections():
    """Sample detection data for testing exporters."""
    return [
        {
            "class_name": "pallet",
            "bbox_2d": {
                "x_min": 100,
                "y_min": 150,
                "x_max": 300,
                "y_max": 400,
                "width": 200,
                "height": 250,
            },
            "confidence": 0.95,
        },
        {
            "class_name": "box",
            "bbox_2d": {
                "x_min": 120,
                "y_min": 170,
                "x_max": 180,
                "y_max": 220,
                "width": 60,
                "height": 50,
            },
            "confidence": 0.87,
        },
    ]


@pytest.fixture
def sample_dataset_info(sample_detections):
    """Sample dataset information for testing."""
    return {
        "frames": [
            {
                "frame_id": 1,
                "image_path": "frame_000001.png",
                "width": 640,
                "height": 480,
                "detections": sample_detections,
            },
            {
                "frame_id": 2,
                "image_path": "frame_000002.png",
                "width": 640,
                "height": 480,
                "detections": [],
            },
        ]
    }


@pytest.fixture
def mock_pallet_object():
    """Mock pallet object for testing."""
    pallet = Mock()
    pallet.name = "test_pallet"
    pallet.type = "MESH"
    pallet.location = MockVector(0, 0, 0)
    pallet.bound_box = [
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ]
    pallet.matrix_world = Mock()
    return pallet


@pytest.fixture
def mock_camera_object():
    """Mock camera object for testing."""
    camera = Mock()
    camera.name = "test_camera"
    camera.type = "CAMERA"
    camera.location = MockVector(5, 5, 5)
    camera.rotation_euler = MockEuler(0, 0, 0)
    camera.data = Mock()
    camera.data.lens = 35.0
    camera.data.sensor_width = 36.0
    return camera
