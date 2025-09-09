"""Simple tests for utility functions."""

import tempfile

from palletdatagenerator.utils import (
    ensure_directory,
    format_file_size,
    setup_logging,
)


def test_ensure_directory():
    """Test directory creation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        import os

        new_dir = os.path.join(tmp_dir, "test_dir")
        result = ensure_directory(new_dir)

        assert result.exists()
        assert result.is_dir()


def test_format_file_size():
    """Test file size formatting."""
    assert format_file_size(1024) == "1 KB"
    assert format_file_size(500) == "500 B"
    assert format_file_size(0) == "0 B"
    assert format_file_size(1536) == "1.5 KB"  # Test with decimal


def test_setup_logging():
    """Test logging setup."""
    # Should not crash
    setup_logging("INFO")
