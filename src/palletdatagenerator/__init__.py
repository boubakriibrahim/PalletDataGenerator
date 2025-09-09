"""PalletDataGenerator - Professional Blender Synthetic Dataset Library

A comprehensive library for generating synthetic pallet and warehouse datasets
using Blender with advanced rendering capabilities, annotation generation,
and export functionalities.

Features:
- Single pallet and warehouse scene generation
- Advanced lighting and camera systems
- Multiple annotation formats (YOLO, COCO, VOC)
- GPU-accelerated rendering
- Professional packaging and CI/CD
"""

__version__ = "0.1.0"
__author__ = "Ibrahim Boubakri"
__email__ = "ibrahim@example.com"
__license__ = "MIT"

from .core.generator import PalletGenerator, WarehouseGenerator
from .core.renderer import BlenderRenderer
from .exporters.coco import COCOExporter
from .exporters.voc import VOCExporter
from .exporters.yolo import YOLOExporter

__all__ = [
    "PalletGenerator",
    "WarehouseGenerator",
    "BlenderRenderer",
    "YOLOExporter",
    "COCOExporter",
    "VOCExporter",
]
