"""
Bitmap renderer for LED matrix displays.

Renders DisplayData to PIL Image objects suitable for 64x32 RGB LED matrices.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from trixhub.providers.base import DisplayData
from trixhub.renderers.base import Renderer
from trixhub.utils.text_helpers import center_text, get_text_bbox


class BitmapRenderer(Renderer):
    """
    Renders DisplayData to PIL Image for LED matrix displays.

    Creates 64x32 RGB bitmaps suitable for Matrix Portal displays.
    """

    def __init__(self, width: int = 64, height: int = 32, font_path: str = None):
        """
        Initialize bitmap renderer.

        Args:
            width: Display width in pixels (default: 64)
            height: Display height in pixels (default: 32)
            font_path: Path to TrueType font file (default: bundled DejaVuSans-Bold)
        """
        self.width = width
        self.height = height

        # Default font path (bundled in Docker image)
        if font_path is None:
            # Try bundled fonts first, fall back to system fonts
            bundled_font = "/app/fonts/DejaVuSans-Bold.ttf"
            system_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

            if os.path.exists(bundled_font):
                font_path = bundled_font
            elif os.path.exists(system_font):
                font_path = system_font
            else:
                # Fall back to default font if nothing else available
                font_path = None

        self.font_path = font_path

    def render(self, data: DisplayData) -> Image.Image:
        """
        Render DisplayData to PIL Image.

        Args:
            data: Structured data from a provider

        Returns:
            PIL Image (RGB mode) sized for LED matrix

        Raises:
            ValueError: If content type is not supported
        """
        content_type = data.content.get("type")

        if content_type == "time":
            return self._render_time(data)
        else:
            return self._render_error(f"Unknown type: {content_type}")

    def _render_time(self, data: DisplayData) -> Image.Image:
        """
        Render time display.

        Shows time centered in large font with ROYGBIV rainbow colors,
        and date at bottom in smaller font.

        Args:
            data: DisplayData with time information

        Returns:
            Rendered PIL Image
        """
        # Create black background
        img = Image.new('RGB', (self.width, self.height), color='black')
        draw = ImageDraw.Draw(img)

        # Load fonts
        if self.font_path:
            time_font = ImageFont.truetype(self.font_path, 12)
            date_font = ImageFont.truetype(self.font_path, 8)
        else:
            time_font = ImageFont.load_default()
            date_font = ImageFont.load_default()

        # Get time string
        time_str = data.content.get("time_12h", "??:??")

        # ROYGBIV rainbow colors
        rainbow_colors = [
            (255, 0, 0),      # Red
            (255, 127, 0),    # Orange
            (255, 255, 0),    # Yellow
            (0, 255, 0),      # Green
            (0, 0, 255),      # Blue
            (75, 0, 130),     # Indigo
            (148, 0, 211),    # Violet
        ]

        # Center time text - calculate starting position
        start_x, y = center_text(time_str, time_font, self.width, self.height)

        # Draw each character in a different color (skip spaces)
        current_x = start_x
        color_index = 0
        for char in time_str:
            # Skip spaces for color assignment
            if char == ' ':
                color = (0, 0, 0)  # Black (invisible on black background)
            else:
                color = rainbow_colors[color_index % len(rainbow_colors)]
                color_index += 1

            draw.text((current_x, y), char, fill=color, font=time_font)

            # Move to next character position
            char_width = draw.textlength(char, font=time_font)
            current_x += char_width

        # Add date at bottom
        date_str = data.content.get("date_short", data.content.get("date", ""))
        if date_str:
            draw.text((2, self.height - 10), date_str, fill='gray', font=date_font)

        return img

    def _render_error(self, message: str) -> Image.Image:
        """
        Render error message.

        Creates red background with white error text.

        Args:
            message: Error message to display

        Returns:
            Rendered PIL Image with error
        """
        # Create red background to make errors obvious
        img = Image.new('RGB', (self.width, self.height), color='red')
        draw = ImageDraw.Draw(img)

        # Load font
        if self.font_path:
            font = ImageFont.truetype(self.font_path, 8)
        else:
            font = ImageFont.load_default()

        # Draw error message
        error_text = f"ERROR:\n{message}"
        draw.text((2, 2), error_text, fill='white', font=font)

        return img

    def get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """
        Get a font of specified size.

        Utility method for getting fonts at different sizes.

        Args:
            size: Font size in points

        Returns:
            ImageFont object
        """
        if self.font_path:
            return ImageFont.truetype(self.font_path, size)
        else:
            return ImageFont.load_default()
