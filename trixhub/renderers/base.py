"""
Base class for renderers.

Renderers convert DisplayData to specific output formats
(bitmaps, ASCII art, HTML, etc.)
"""

from abc import ABC, abstractmethod
from typing import Any
from trixhub.providers.base import DisplayData


class Renderer(ABC):
    """
    Base class for renderers.

    Renderers convert provider-generated DisplayData into specific output
    formats like bitmaps, ASCII art, HTML, etc.

    The return type of render() varies by renderer implementation.
    """

    @abstractmethod
    def render(self, data: DisplayData) -> Any:
        """
        Render DisplayData to target format.

        Args:
            data: Structured data from a provider

        Returns:
            Rendered output (type varies by renderer implementation)
            - BitmapRenderer: PIL Image.Image
            - ASCIIRenderer: str
            - HTMLRenderer: str
            etc.

        Raises:
            ValueError: If data content type is not supported
        """
        pass
