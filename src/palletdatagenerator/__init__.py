"""
PalletDataGenerator - Unified Blender library for synthetic pallet dataset generation.

This library provides a simplified, unified approach to generating synthetic pallet datasets
with embedded configuration and auto-batch management.
"""

from .config import DefaultConfig
from .generator import PalletDataGenerator
from .utils import setup_logging

__version__ = "0.1.2"
__author__ = "Ibrahim Boubakri"
__email__ = "ibrahimbouakri1@gmail.com"

# Main exports
__all__ = [
    "PalletDataGenerator",
    "DefaultConfig",
    "setup_logging",
]

# Convenience aliases for backward compatibility
Generator = PalletDataGenerator  # Alias for main generator class
Config = DefaultConfig  # Alias for config class
