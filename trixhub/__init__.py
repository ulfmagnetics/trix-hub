"""
trix-hub: Data aggregation and rendering hub for LED matrix displays.

A flexible architecture for fetching data from various sources and rendering
them to different output formats, primarily for Matrix Portal LED displays.
"""

__version__ = "0.1.0"

# Import main classes for convenience
from trixhub.providers.base import DisplayData, DataProvider
from trixhub.renderers.base import Renderer

__all__ = [
    "DisplayData",
    "DataProvider",
    "Renderer",
]
