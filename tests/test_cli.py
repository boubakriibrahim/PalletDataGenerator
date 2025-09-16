"""Tests for CLI functionality."""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from palletdatagenerator.cli import create_parser, main


class TestCLI:
    """Test suite for CLI functionality."""

    def test_parse_arguments_defaults(self):
        """Test argument parsing with default values."""
        parser = create_parser()
        args = parser.parse_args(["test_scene.blend"])

        assert args.scene_path == Path("test_scene.blend")
        assert args.mode == "single_pallet"
        assert args.frames == 50
        assert args.resolution == [1024, 768]
        assert args.output is None

    def test_parse_arguments_warehouse_mode(self):
        """Test parsing warehouse mode arguments."""
        parser = create_parser()
        args = parser.parse_args(
            ["test_scene.blend", "--mode", "warehouse", "--frames", "100"]
        )

        assert args.mode == "warehouse"
        assert args.frames == 100

    def test_parse_arguments_custom_resolution(self):
        """Test parsing custom resolution arguments."""
        parser = create_parser()
        args = parser.parse_args(["test_scene.blend", "--resolution", "1920", "1080"])

        assert args.resolution == [1920, 1080]

    def test_parse_arguments_custom_output(self):
        """Test parsing custom output directory."""
        parser = create_parser()
        args = parser.parse_args(["test_scene.blend", "--output", "/custom/output"])

        assert args.output == Path("/custom/output")

    def test_parse_arguments_all_options(self):
        """Test parsing all available options."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "test_scene.blend",
                "--mode",
                "warehouse",
                "--frames",
                "200",
                "--resolution",
                "2048",
                "1536",
                "--output",
                "/my/output",
            ]
        )

        assert args.scene_path == Path("test_scene.blend")
        assert args.mode == "warehouse"
        assert args.frames == 200
        assert args.resolution == [2048, 1536]
        assert args.output == Path("/my/output")

    def test_invalid_mode_argument(self):
        """Test that invalid mode raises appropriate error."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["test_scene.blend", "--mode", "invalid_mode"])

    def test_invalid_resolution_format(self):
        """Test that invalid resolution format raises error."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["test_scene.blend", "--resolution", "1024"]  # Missing height
            )

    def test_negative_frames(self):
        """Test that negative frames value is handled."""
        # The argument parser should accept negative values, but the application should handle them
        parser = create_parser()
        args = parser.parse_args(["test_scene.blend", "--frames", "-10"])

        assert args.frames == -10

    @patch("palletdatagenerator.cli.PalletDataGenerator")
    @patch("palletdatagenerator.cli.RUNNING_IN_BLENDER", True)
    def test_main_function_single_pallet(
        self, mock_generator_class, sample_scene_file: Path, temp_dir: Path
    ):
        """Test main function with single pallet mode."""
        mock_generator = Mock()
        mock_generator.generate.return_value = {
            "output_path": str(temp_dir),
            "frames": 5,
            "mode": "single_pallet",
        }
        mock_generator_class.return_value = mock_generator

        # Mock sys.argv
        test_args = [
            "palletgen",
            str(sample_scene_file),
            "--mode",
            "single_pallet",
            "--frames",
            "5",
            "--output",
            str(temp_dir),
        ]

        with patch.object(sys, "argv", test_args):
            main()

        # Verify that PalletDataGenerator was called with correct arguments
        mock_generator_class.assert_called_once_with(mode="single_pallet")

        # Verify that generate was called
        mock_generator.generate.assert_called_once_with(
            scene_path=sample_scene_file,
            num_frames=5,
            output_dir=temp_dir,
            resolution=[1024, 768],
        )

    @patch("palletdatagenerator.cli.PalletDataGenerator")
    @patch("palletdatagenerator.cli.RUNNING_IN_BLENDER", True)
    def test_main_function_warehouse(
        self, mock_generator_class, sample_scene_file: Path, temp_dir: Path
    ):
        """Test main function with warehouse mode."""
        mock_generator = Mock()
        mock_generator.generate.return_value = {
            "output_path": str(temp_dir),
            "frames": 10,
            "mode": "warehouse",
        }
        mock_generator_class.return_value = mock_generator

        test_args = [
            "palletgen",
            str(sample_scene_file),
            "--mode",
            "warehouse",
            "--frames",
            "10",
        ]

        with patch.object(sys, "argv", test_args):
            main()

        mock_generator_class.assert_called_once_with(mode="warehouse")

        mock_generator.generate.assert_called_once_with(
            scene_path=sample_scene_file,
            num_frames=10,
            output_dir=None,
            resolution=[1024, 768],
        )

    @patch("palletdatagenerator.cli.PalletDataGenerator")
    @patch("palletdatagenerator.cli.RUNNING_IN_BLENDER", True)
    def test_main_function_with_resolution(
        self, mock_generator_class, sample_scene_file: Path
    ):
        """Test main function with custom resolution."""
        mock_generator = Mock()
        mock_generator.generate.return_value = {
            "output_path": "/test/output",
            "frames": 3,
            "mode": "single_pallet",
        }
        mock_generator_class.return_value = mock_generator

        test_args = [
            "palletgen",
            str(sample_scene_file),
            "--resolution",
            "1920",
            "1080",
            "--frames",
            "3",
        ]

        with patch.object(sys, "argv", test_args):
            main()

        # Verify generate was called with custom resolution
        mock_generator.generate.assert_called_once_with(
            scene_path=sample_scene_file,
            num_frames=3,
            output_dir=None,
            resolution=[1920, 1080],
        )

    @patch("palletdatagenerator.cli.PalletDataGenerator")
    @patch("palletdatagenerator.cli.RUNNING_IN_BLENDER", True)
    def test_main_function_error_handling(
        self, mock_generator_class, sample_scene_file: Path
    ):
        """Test main function error handling."""
        mock_generator = Mock()
        mock_generator.generate.side_effect = Exception("Test error")
        mock_generator_class.return_value = mock_generator

        test_args = ["palletgen", str(sample_scene_file)]

        with patch.object(sys, "argv", test_args), pytest.raises(SystemExit):
            main()

    def test_help_output(self):
        """Test that help output is generated correctly."""
        parser = create_parser()
        with patch("sys.stderr", StringIO()), pytest.raises(SystemExit):
            parser.parse_args(["--help"])

        # The help should have been written to stderr (or stdout)

    def test_missing_scene_path(self):
        """Test that missing scene path argument raises error."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_scene_path_validation(self):
        """Test scene path validation in argument parsing."""
        # Valid scene path
        parser = create_parser()
        args = parser.parse_args(["valid_scene.blend"])
        assert args.scene_path == Path("valid_scene.blend")

        # The actual file existence check should happen in the main application,
        # not in argument parsing
