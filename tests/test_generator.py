"""Tests for the main PalletDataGenerator class."""

from pathlib import Path
from unittest.mock import patch

import pytest

from palletdatagenerator import PalletDataGenerator


class TestPalletDataGenerator:
    """Test suite for PalletDataGenerator class."""

    def test_init_with_defaults(self, temp_dir: Path, sample_scene_file: Path):
        """Test generator initialization with default parameters."""
        generator = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )

        assert generator.scene_path == str(sample_scene_file)
        assert generator.mode == "single_pallet"

    def test_init_invalid_mode(self, sample_scene_file: Path, temp_dir: Path):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Mode must be"):
            PalletDataGenerator(mode="invalid_mode", scene_path=str(sample_scene_file))

    def test_init_nonexistent_scene(self, temp_dir: Path):
        """Test that nonexistent scene file can be passed (validation happens in generate())."""
        nonexistent_scene = temp_dir / "nonexistent.blend"

        # Constructor should not validate scene file existence
        generator = PalletDataGenerator(
            mode="single_pallet", scene_path=str(nonexistent_scene)
        )
        assert generator.scene_path == str(nonexistent_scene)

    def test_warehouse_mode_initialization(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test warehouse mode initialization."""
        generator = PalletDataGenerator(
            mode="warehouse", scene_path=str(sample_scene_file)
        )

        assert generator.mode == "warehouse"

    @patch("palletdatagenerator.generator.BLENDER_AVAILABLE", True)
    def test_blender_available_initialization(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test initialization when Blender is available."""
        with patch("palletdatagenerator.generator.ensure_dependencies") as mock_ensure:
            PalletDataGenerator(mode="single_pallet", scene_path=str(sample_scene_file))
            mock_ensure.assert_called_once()

    def test_generate_method_signature(self, sample_scene_file: Path, temp_dir: Path):
        """Test generate method exists and has correct signature."""
        generator = PalletDataGenerator(mode="single_pallet")

        # Just check the method exists - actual functionality would require Blender
        assert hasattr(generator, "generate")

        # Test would fail in non-Blender environment, so just verify signature exists
        import inspect

        sig = inspect.signature(generator.generate)
        expected_params = ["scene_path", "num_frames", "output_dir", "resolution"]
        for param in expected_params:
            assert param in sig.parameters

    def test_mode_attribute_access(self, sample_scene_file: Path, temp_dir: Path):
        """Test that generator mode and scene_path are accessible."""
        generator = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )

        # Test basic attributes
        assert generator.mode == "single_pallet"
        assert generator.scene_path == str(sample_scene_file)

        # Test different mode
        warehouse_gen = PalletDataGenerator(mode="warehouse")
        assert warehouse_gen.mode == "warehouse"
        assert warehouse_gen.scene_path is None

    @patch("palletdatagenerator.generator.BLENDER_AVAILABLE", False)
    def test_generate_without_blender_raises_error(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test that calling generate without Blender raises RuntimeError."""
        generator = PalletDataGenerator(mode="single_pallet")

        with pytest.raises(RuntimeError, match="Blender is not available"):
            generator.generate(
                scene_path=sample_scene_file, num_frames=5, output_dir=temp_dir
            )

    def test_default_values(self):
        """Test generator initialization with default values."""
        generator = PalletDataGenerator()  # No arguments - should use defaults

        assert generator.mode == "single_pallet"  # Default mode
        assert generator.scene_path is None  # Default scene_path

        generator2 = PalletDataGenerator(mode="warehouse")
        assert generator2.mode == "warehouse"
        assert generator2.scene_path is None

    def test_blender_unavailable_initialization(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test initialization when Blender is not available."""
        with patch("palletdatagenerator.generator.BLENDER_AVAILABLE", False):
            # Should still initialize successfully
            generator = PalletDataGenerator(
                mode="single_pallet", scene_path=str(sample_scene_file)
            )
            assert generator.mode == "single_pallet"
            assert generator.scene_path == str(sample_scene_file)

    def test_mode_validation(self, sample_scene_file: Path, temp_dir: Path):
        """Test that mode validation works correctly."""
        # Valid modes should work
        for mode in ["single_pallet", "warehouse"]:
            generator = PalletDataGenerator(
                mode=mode, scene_path=str(sample_scene_file)
            )
            assert generator.mode == mode

        # Invalid mode should raise ValueError
        with pytest.raises(ValueError, match="Mode must be"):
            PalletDataGenerator(mode="invalid_mode")
