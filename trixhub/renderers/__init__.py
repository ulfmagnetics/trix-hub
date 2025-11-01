"""
Renderers for trix-hub.

Renderers convert DisplayData to specific output formats.
"""

from trixhub.renderers.base import Renderer
from trixhub.renderers.bitmap import BitmapRenderer
from trixhub.renderers.ascii import ASCIIRenderer

__all__ = [
    "Renderer",
    "BitmapRenderer",
    "ASCIIRenderer",
]
