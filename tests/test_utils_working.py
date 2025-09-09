"""Tests for utility functions."""

from pathlib import Path

from palletdatagenerator.utils import (
    ensure_directory,
    format_file_size,
    load_config,
    save_config,
    setup_logging,
)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_ensure_directory_creates_directory(self, temp_output_dir):
        """Test that ensure_directory creates directory."""
        new_dir = Path(temp_output_dir) / "new_directory"
        assert not new_dir.exists()

        result = ensure_directory(str(new_dir))
        assert result.exists()
        assert result.is_dir()

    def test_ensure_directory_with_existing_directory(self, temp_output_dir):
        """Test that ensure_directory works with existing directory."""
        # Should not raise error
        result = ensure_directory(temp_output_dir)
        assert result.exists()

    def test_ensure_directory_creates_nested_directories(self, temp_output_dir):
        """Test creating nested directories."""
        nested_dir = Path(temp_output_dir) / "level1" / "level2" / "level3"
        assert not nested_dir.exists()

        result = ensure_directory(str(nested_dir))
        assert result.exists()
        assert result.is_dir()

    def test_load_config_yaml(self, temp_output_dir):
        """Test loading YAML config file."""
        config_file = Path(temp_output_dir) / "test_config.yaml"
        config_file.write_text("test_key: test_value\nnumber: 42\n")

        config = load_config(str(config_file))
        assert config["test_key"] == "test_value"
        assert config["number"] == 42

    def test_save_config_yaml(self, temp_output_dir):
        """Test saving YAML config file."""
        config_file = Path(temp_output_dir) / "output_config.yaml"
        test_config = {"key1": "value1", "key2": 123}

        save_config(test_config, str(config_file))

        assert config_file.exists()
        loaded_config = load_config(str(config_file))
        assert loaded_config == test_config

    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(1024) == "1 KB"
        assert format_file_size(500) == "500 B"
        assert format_file_size(0) == "0 B"
        assert format_file_size(1536) == "1.5 KB"  # Test with decimal

    def test_setup_logging(self):
        """Test logging setup."""
        # Should not raise any errors
        setup_logging()
        setup_logging(level="DEBUG")
