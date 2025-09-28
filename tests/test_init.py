"""Tests for package initialization and imports."""

import pytest


class TestPackageInit:
    """Test suite for package initialization."""

    def test_package_imports(self):
        """Test that main package imports work correctly."""
        # Test main imports
        from palletdatagenerator import (
            DefaultConfig,
            PalletDataGenerator,
            setup_logging,
        )

        # These should not raise ImportError
        assert PalletDataGenerator is not None
        assert DefaultConfig is not None
        assert setup_logging is not None

    def test_version_import(self):
        """Test that version can be imported."""
        from palletdatagenerator import __version__

        assert isinstance(__version__, str)
        assert len(__version__) > 0
        assert "." in __version__  # Should be in format like "0.1.3"

    def test_author_info(self):
        """Test that author information is available."""
        from palletdatagenerator import __author__, __email__

        assert isinstance(__author__, str)
        assert len(__author__) > 0
        assert isinstance(__email__, str)
        assert "@" in __email__

    def test_all_exports(self):
        """Test that __all__ exports are correct."""
        from palletdatagenerator import __all__

        assert isinstance(__all__, list)
        assert len(__all__) > 0

        # Test that all exported items can be imported
        import palletdatagenerator

        for item in __all__:
            assert hasattr(palletdatagenerator, item), f"Missing export: {item}"

    def test_convenience_aliases(self):
        """Test that convenience aliases work."""
        from palletdatagenerator import (
            Config,
            DefaultConfig,
            Generator,
            PalletDataGenerator,
        )

        # Test that aliases point to the same classes
        assert Generator is PalletDataGenerator
        assert Config is DefaultConfig

    def test_package_docstring(self):
        """Test that package has docstring."""
        import palletdatagenerator

        assert palletdatagenerator.__doc__ is not None
        assert len(palletdatagenerator.__doc__.strip()) > 0

    def test_submodule_imports(self):
        """Test that submodules can be imported."""
        # These should not raise ImportError
        from palletdatagenerator import config, utils

        assert config is not None
        assert utils is not None

    def test_version_format(self):
        """Test that version follows semantic versioning format."""
        import re

        from palletdatagenerator import __version__

        # Basic semantic versioning pattern
        semver_pattern = r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?(?:\+[a-zA-Z0-9]+)?$"
        assert re.match(
            semver_pattern, __version__
        ), f"Invalid version format: {__version__}"

    def test_no_import_errors(self):
        """Test that importing the package doesn't raise any errors."""
        try:
            import palletdatagenerator

            # Try to access main attributes
            _ = palletdatagenerator.__version__
            _ = palletdatagenerator.PalletDataGenerator
            _ = palletdatagenerator.DefaultConfig
            _ = palletdatagenerator.setup_logging
        except Exception as e:
            pytest.fail(f"Package import failed with error: {e}")

    def test_circular_imports(self):
        """Test that there are no circular import issues."""
        # Import main modules that might have circular dependencies
        import importlib.util

        for mod in ["cli", "config", "generator", "utils"]:
            spec = importlib.util.find_spec(f"palletdatagenerator.{mod}")
            if spec is None:
                pytest.fail(f"Circular import detected: {mod}")

    def test_module_attributes_exist(self):
        """Test that expected module attributes exist."""
        import palletdatagenerator

        required_attrs = [
            "__version__",
            "__author__",
            "__email__",
            "__all__",
            "PalletDataGenerator",
            "DefaultConfig",
            "setup_logging",
        ]

        for attr in required_attrs:
            assert hasattr(palletdatagenerator, attr), f"Missing attribute: {attr}"

    def test_module_level_constants(self):
        """Test that module-level constants are properly defined."""
        import palletdatagenerator

        # Test that constants are of expected types
        assert isinstance(palletdatagenerator.__version__, str)
        assert isinstance(palletdatagenerator.__author__, str)
        assert isinstance(palletdatagenerator.__email__, str)
        assert isinstance(palletdatagenerator.__all__, list)

    def test_import_performance(self):
        """Test that package import is reasonably fast."""
        import time

        start_time = time.time()

        end_time = time.time()

        # Import should complete within reasonable time
        import_time = end_time - start_time
        assert import_time < 2.0, f"Package import took too long: {import_time}s"
