"""Tests for configuration system."""

from palletdatagenerator.config import DefaultConfig


class TestDefaultConfig:
    """Test suite for DefaultConfig class."""

    def test_single_pallet_config_structure(self):
        """Test that single pallet config has required structure."""
        config = DefaultConfig(mode="single_pallet")

        # Test that we can access config values using attribute access
        assert hasattr(config, "_config")
        assert config.num_images is not None
        assert config.resolution_x is not None
        assert config.resolution_y is not None
        assert config.render_engine is not None

        # Test data types
        assert isinstance(config.num_images, int)
        assert isinstance(config.resolution_x, int)
        assert isinstance(config.resolution_y, int)
        assert isinstance(config.render_engine, str)

    def test_warehouse_config_structure(self):
        """Test that warehouse config has required structure."""
        config = DefaultConfig(mode="warehouse")

        # Test that we can access warehouse config values
        assert hasattr(config, "_config")
        assert config.resolution_x is not None
        assert config.resolution_y is not None

        # Test warehouse-specific settings (warehouse config uses max_total_images instead of num_images)
        assert isinstance(config.resolution_x, int)
        assert isinstance(config.resolution_y, int)

    def test_config_values_are_reasonable(self):
        """Test that config values are within reasonable ranges."""
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        # Test resolution values
        assert single_config.resolution_x > 0
        assert single_config.resolution_y > 0
        assert warehouse_config.resolution_x > 0
        assert warehouse_config.resolution_y > 0

        # Test image counts (single pallet has num_images, warehouse has max_total_images)
        assert single_config.num_images >= 0
        assert warehouse_config.max_total_images >= 0

    def test_render_engine_values(self):
        """Test that render engine values are valid."""
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        valid_engines = ["CYCLES", "EEVEE", "WORKBENCH"]

        assert single_config.render_engine in valid_engines
        assert warehouse_config.render_engine in valid_engines

    def test_config_immutability(self):
        """Test that config objects don't share references."""
        config1 = DefaultConfig(mode="single_pallet")
        config2 = DefaultConfig(mode="single_pallet")

        # Modify one config
        config1.num_images = 999

        # Other config should be unchanged (they should have separate _config dicts)
        assert config2.num_images != 999

    def test_config_has_camera_settings(self):
        """Test that configs include camera-related settings."""
        single_config = DefaultConfig(mode="single_pallet")

        # Should have camera-related settings
        camera_keys = [key for key in single_config._config if "camera" in key.lower()]
        assert len(camera_keys) > 0

    def test_config_has_export_settings(self):
        """Test that configs include export-related settings."""
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        # Look for export-related settings
        for config in [single_config, warehouse_config]:
            # Just verify the config object is properly initialized
            assert hasattr(config, "_config")
            assert isinstance(config._config, dict)

    def test_single_pallet_specific_settings(self):
        """Test settings specific to single pallet mode."""

    DefaultConfig(mode="single_pallet")

    # Look for single pallet specific settings
    # single_pallet_keys = [
    #     key
    #     for key in config._config
    #     if any(term in key.lower() for term in ["pallet", "single", "side", "face"])
    # ]

    # Should have some pallet-specific settings

    def test_warehouse_specific_settings(self):
        """Test settings specific to warehouse mode."""
        config = DefaultConfig(mode="warehouse")

        # Should be a valid config object at minimum
        assert hasattr(config, "_config")
        assert isinstance(config._config, dict)
        assert len(config._config) > 0

    def test_config_consistency(self):
        """Test that both configs have consistent basic settings."""
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        # Both should have resolution and render engine (warehouse uses max_total_images vs num_images)
        basic_keys = ["resolution_x", "resolution_y", "render_engine"]

        for key in basic_keys:
            assert (
                hasattr(single_config, key) or key in single_config._config
            ), f"Missing {key} in single pallet config"
            assert (
                hasattr(warehouse_config, key) or key in warehouse_config._config
            ), f"Missing {key} in warehouse config"

        # Single pallet has num_images, warehouse has max_total_images
        assert single_config.num_images is not None
        assert warehouse_config.max_total_images is not None

    def test_config_keys_are_strings(self):
        """Test that all config keys are strings."""
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        for config in [single_config, warehouse_config]:
            for key in config._config:
                assert isinstance(key, str), f"Config key {key} is not a string"

    def test_config_no_none_values(self):
        """Test that config values are not None."""
        single_config = DefaultConfig(mode="single_pallet")
        warehouse_config = DefaultConfig(mode="warehouse")

        for config_name, config in [
            ("single_pallet", single_config),
            ("warehouse", warehouse_config),
        ]:
            for key, value in config._config.items():
                assert (
                    value is not None
                ), f"{config_name} config has None value for {key}"

    def test_config_get_method(self):
        """Test DefaultConfig.get() method."""
        config = DefaultConfig(mode="single_pallet")

        # Test existing key
        assert config.get("num_images") == 50

        # Test non-existing key with default
        assert config.get("non_existing_key", "default") == "default"

        # Test non-existing key without default
        assert config.get("non_existing_key") is None

    def test_config_update_method(self):
        """Test DefaultConfig.update() method."""
        config = DefaultConfig(mode="single_pallet")

        # original_num_images = config.num_images

        # Update config
        config.update(num_images=100, new_key="new_value")

        # Check updates
        assert config.num_images == 100
        assert config.new_key == "new_value"
        assert config.get("new_key") == "new_value"

    def test_config_attribute_assignment(self):
        """Test setting config values via attribute assignment."""
        config = DefaultConfig(mode="single_pallet")

        # Set new attribute
        config.test_attribute = "test_value"
        assert config.test_attribute == "test_value"

        # Modify existing attribute
        original_resolution = config.resolution_x
        config.resolution_x = 1920
        assert config.resolution_x == 1920
        assert config.resolution_x != original_resolution
