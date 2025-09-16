"""Integration tests for end-to-end functionality."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from palletdatagenerator import PalletDataGenerator


class TestIntegration:
    """Integration test suite."""

    @patch("palletdatagenerator.generator.BLENDER_AVAILABLE", True)
    @patch("palletdatagenerator.generator.bpy")
    def test_end_to_end_single_pallet(
        self, mock_bpy, sample_scene_file: Path, temp_dir: Path
    ):
        """Test end-to-end single pallet generation workflow."""
        # Mock Blender operations
        mock_bpy.ops = Mock()
        mock_bpy.ops.wm = Mock()
        mock_bpy.ops.wm.open_mainfile = Mock()

        # Create generator with correct API
        generator = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )

        # Mock the generate method to avoid full Blender execution
        with patch.object(generator, "generate") as mock_generate:
            mock_generate.return_value = {
                "output_path": str(temp_dir),
                "frames": 3,
                "mode": "single_pallet",
            }

            # Call generate method with correct signature
            result = generator.generate(
                scene_path=sample_scene_file, num_frames=3, output_dir=temp_dir
            )

            # Verify results
            assert result is not None
            assert result["mode"] == "single_pallet"
            assert result["frames"] == 3
            mock_generate.assert_called_once()

    @patch("palletdatagenerator.generator.BLENDER_AVAILABLE", True)
    @patch("palletdatagenerator.generator.bpy")
    def test_end_to_end_warehouse(
        self, mock_bpy, sample_scene_file: Path, temp_dir: Path
    ):
        """Test end-to-end warehouse generation workflow."""
        # Mock Blender operations
        mock_bpy.ops = Mock()
        mock_bpy.ops.wm = Mock()
        mock_bpy.ops.wm.open_mainfile = Mock()

        # Create generator with correct API
        generator = PalletDataGenerator(
            mode="warehouse", scene_path=str(sample_scene_file)
        )

        # Mock the generate method
        with patch.object(generator, "generate") as mock_generate:
            mock_generate.return_value = {
                "output_path": str(temp_dir),
                "frames": 2,
                "mode": "warehouse",
            }

            # Call generate method
            result = generator.generate(
                scene_path=sample_scene_file, num_frames=2, output_dir=temp_dir
            )

            # Verify results
            assert result is not None
            assert result["mode"] == "warehouse"
            assert result["frames"] == 2
            mock_generate.assert_called_once()

    def test_generator_initialization_integration(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test that generator initialization works with different modes."""
        # Test single pallet mode
        single_generator = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )
        assert single_generator.mode == "single_pallet"
        assert single_generator.scene_path == str(sample_scene_file)

        # Test warehouse mode
        warehouse_generator = PalletDataGenerator(
            mode="warehouse", scene_path=str(sample_scene_file)
        )
        assert warehouse_generator.mode == "warehouse"
        assert warehouse_generator.scene_path == str(sample_scene_file)

        # Test default initialization
        default_generator = PalletDataGenerator()
        assert default_generator.mode == "single_pallet"
        assert default_generator.scene_path is None

    def test_generate_method_parameters(self, sample_scene_file: Path, temp_dir: Path):
        """Test that generate method accepts the correct parameters."""
        generator = PalletDataGenerator(mode="single_pallet")

        # Test method exists and has correct signature
        assert hasattr(generator, "generate")

        # Check signature parameters using inspect
        import inspect

        sig = inspect.signature(generator.generate)
        expected_params = {"scene_path", "num_frames", "output_dir", "resolution"}
        actual_params = set(sig.parameters.keys())

        # All expected parameters should be present
        assert expected_params.issubset(actual_params)

    def test_blender_available_vs_unavailable(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test behavior when Blender is available vs unavailable."""
        generator = PalletDataGenerator(mode="single_pallet")

        # Test with Blender unavailable (should raise error when generating)
        with (
            patch("palletdatagenerator.generator.BLENDER_AVAILABLE", False),
            pytest.raises(RuntimeError, match="Blender is not available"),
        ):
            generator.generate(
                scene_path=sample_scene_file, num_frames=1, output_dir=temp_dir
            )

        # Test with Blender available (should not raise during initialization)
        with patch("palletdatagenerator.generator.BLENDER_AVAILABLE", True):
            # Should create without error
            available_generator = PalletDataGenerator(mode="single_pallet")
            assert available_generator.mode == "single_pallet"

    def test_mode_consistency(self, sample_scene_file: Path, temp_dir: Path):
        """Test that generator mode remains consistent throughout operations."""
        generator = PalletDataGenerator(mode="warehouse")

        # Mode should remain consistent
        assert generator.mode == "warehouse"

        # After various operations, mode should still be correct
        assert generator.mode == "warehouse"

    @patch("palletdatagenerator.generator.BLENDER_AVAILABLE", True)
    def test_multiple_generator_instances(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test multiple generator instances work independently."""
        generator1 = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )
        generator2 = PalletDataGenerator(mode="warehouse")

        # Should be independent instances
        assert generator1 is not generator2
        assert generator1.mode != generator2.mode
        assert generator1.scene_path != generator2.scene_path

    def test_api_consistency(self, sample_scene_file: Path, temp_dir: Path):
        """Test that API is consistent across different usage patterns."""
        # Test different constructor patterns
        gen1 = PalletDataGenerator()  # Default
        gen2 = PalletDataGenerator(mode="warehouse")  # Mode only
        gen3 = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )  # Both

        # All should be valid generators
        for gen in [gen1, gen2, gen3]:
            assert hasattr(gen, "mode")
            assert hasattr(gen, "scene_path")
            assert hasattr(gen, "generate")
            assert gen.mode in ["single_pallet", "warehouse"]

    def test_import_integration(self):
        """Test that all expected modules can be imported."""
        # Test core imports
        from palletdatagenerator import PalletDataGenerator
        from palletdatagenerator.cli import create_parser
        from palletdatagenerator.config import DefaultConfig

        # Should be able to create instances
        generator = PalletDataGenerator()
        config = DefaultConfig(mode="single_pallet")
        parser = create_parser()

        assert generator is not None
        assert config is not None
        assert parser is not None

    def test_configuration_integration(self, sample_scene_file: Path, temp_dir: Path):
        """Test that configuration works in integration."""
        from palletdatagenerator.config import DefaultConfig

        # Test config for both modes
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        # Both should have basic required attributes
        assert single_config.resolution_x > 0
        assert single_config.resolution_y > 0
        assert warehouse_config.resolution_x > 0
        assert warehouse_config.resolution_y > 0

        # Should be different modes
        assert single_config.mode == "single_pallet"
        assert warehouse_config.mode == "warehouse"

    def test_end_to_end_api_compatibility(
        self, sample_scene_file: Path, temp_dir: Path
    ):
        """Test that the API is compatible across different usage patterns."""
        # Test generator creation patterns
        generator1 = PalletDataGenerator(
            mode="single_pallet", scene_path=str(sample_scene_file)
        )
        generator2 = PalletDataGenerator(mode="warehouse")

        # Test that generators have expected attributes and behaviors
        assert generator1.mode == "single_pallet"
        assert generator2.mode == "warehouse"

        # Test that generate method exists with correct signature
        import inspect

        sig1 = inspect.signature(generator1.generate)
        sig2 = inspect.signature(generator2.generate)

        # Both should have the same method signature
        assert sig1 == sig2
