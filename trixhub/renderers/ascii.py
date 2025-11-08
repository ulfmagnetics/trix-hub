"""
ASCII renderer for terminal debugging with colored pixels.

Renders DisplayData as colored block characters for terminal output.
Uses half-block technique (▄) with ANSI color codes to display 64x32 bitmaps
as 64x16 terminal characters, providing pixel-perfect terminal preview.
"""

import os
from PIL import Image
from trixhub.providers.base import DisplayData
from trixhub.renderers.base import Renderer
from trixhub.renderers.bitmap import BitmapRenderer


class ASCIIRenderer(Renderer):
    """
    Renders DisplayData as colored pixel blocks for terminal display.

    Uses the half-block technique (▄ U+2584) where each terminal cell
    displays two vertical pixels using foreground and background colors.
    Automatically detects terminal color capabilities and falls back to
    256-color mode if 24-bit true color is not available.
    """

    def __init__(self, width: int = 64, height: int = 32):
        """
        Initialize ASCII renderer.

        Args:
            width: Display width in pixels (default: 64)
            height: Display height in pixels (default: 32)
        """
        self.width = width
        self.height = height
        self.bitmap_renderer = BitmapRenderer(width, height)

        # Detect terminal color capabilities
        self.true_color = self._detect_true_color()

        # ANSI escape codes
        self.RESET = "\033[0m"
        self.LOWER_HALF_BLOCK = "▄"

    def _detect_true_color(self) -> bool:
        """
        Detect if terminal supports 24-bit true color.

        Checks COLORTERM environment variable for "truecolor" or "24bit".
        Falls back to 256-color mode if not detected.

        Returns:
            True if 24-bit color is supported, False otherwise
        """
        colorterm = os.environ.get("COLORTERM", "").lower()
        return colorterm in ("truecolor", "24bit")

    def render(self, data: DisplayData) -> str:
        """
        Render DisplayData to colored ASCII art string.

        Args:
            data: Structured data from a provider

        Returns:
            Multi-line colored ASCII art string using half-block technique

        Raises:
            ValueError: If content type is not supported
        """
        # Use BitmapRenderer to get PIL Image
        img = self.bitmap_renderer.render(data)

        # Convert image to colored ASCII
        return self._image_to_ascii(img)

    def _image_to_ascii(self, img: Image.Image) -> str:
        """
        Convert PIL Image to colored ASCII using half-block technique.

        Each terminal cell displays 2 vertical pixels:
        - Background color = top pixel
        - Foreground color = bottom pixel
        - Character: ▄ (lower half block)

        Args:
            img: PIL Image to convert (RGB mode)

        Returns:
            Colored ASCII string representation
        """
        # Ensure image is in RGB mode
        if img.mode != 'RGB':
            img = img.convert('RGB')

        pixels = img.load()
        output_lines = []

        # Process image in pairs of rows (each pair becomes one terminal row)
        for row_pair in range(0, self.height, 2):
            line = ""

            for col in range(self.width):
                # Get top and bottom pixels
                top_pixel = pixels[col, row_pair]

                # Handle odd heights (last row might not have a pair)
                if row_pair + 1 < self.height:
                    bottom_pixel = pixels[col, row_pair + 1]
                else:
                    bottom_pixel = (0, 0, 0)  # Black for missing pixel

                # Create colored character
                if self.true_color:
                    line += self._rgb_half_block(top_pixel, bottom_pixel)
                else:
                    line += self._256_half_block(top_pixel, bottom_pixel)

            # Reset color at end of line
            line += self.RESET
            output_lines.append(line)

        return "\n".join(output_lines)

    def _rgb_half_block(self, top_rgb: tuple, bottom_rgb: tuple) -> str:
        """
        Create half-block character with 24-bit true color.

        Args:
            top_rgb: RGB tuple for top pixel (background)
            bottom_rgb: RGB tuple for bottom pixel (foreground)

        Returns:
            ANSI colored character string
        """
        r_top, g_top, b_top = top_rgb
        r_bot, g_bot, b_bot = bottom_rgb

        # Background (top pixel) + Foreground (bottom pixel) + Character
        return f"\033[48;2;{r_top};{g_top};{b_top}m\033[38;2;{r_bot};{g_bot};{b_bot}m{self.LOWER_HALF_BLOCK}"

    def _256_half_block(self, top_rgb: tuple, bottom_rgb: tuple) -> str:
        """
        Create half-block character with 256-color palette.

        Quantizes RGB values to nearest 256-color palette index.

        Args:
            top_rgb: RGB tuple for top pixel (background)
            bottom_rgb: RGB tuple for bottom pixel (foreground)

        Returns:
            ANSI colored character string
        """
        top_color = self._rgb_to_256(top_rgb)
        bot_color = self._rgb_to_256(bottom_rgb)

        # Background (top pixel) + Foreground (bottom pixel) + Character
        return f"\033[48;5;{top_color}m\033[38;5;{bot_color}m{self.LOWER_HALF_BLOCK}"

    def _rgb_to_256(self, rgb: tuple) -> int:
        """
        Convert RGB color to nearest 256-color palette index.

        Uses the standard 256-color palette layout:
        - Colors 0-15: System colors (not used for quantization)
        - Colors 16-231: 6x6x6 RGB cube (216 colors)
        - Colors 232-255: Grayscale ramp (24 shades)

        Args:
            rgb: RGB tuple (r, g, b) with values 0-255

        Returns:
            256-color palette index (16-255)
        """
        r, g, b = rgb

        # Check if it's a grayscale color
        if r == g == b:
            # Use grayscale ramp (232-255)
            # Map 0-255 to 0-23 (24 grayscale steps)
            if r < 8:
                return 16  # Black from RGB cube
            elif r > 247:
                return 231  # White from RGB cube
            else:
                gray_index = round((r - 8) / 247 * 23)
                return 232 + gray_index

        # Use 6x6x6 RGB cube (colors 16-231)
        # Quantize each channel to 0-5
        r_index = round(r / 255 * 5)
        g_index = round(g / 255 * 5)
        b_index = round(b / 255 * 5)

        # Calculate palette index
        return 16 + (r_index * 36) + (g_index * 6) + b_index

    def render_frame(self, data: DisplayData, title: str = None) -> str:
        """
        Render with optional title above the frame.

        Useful for debugging multiple providers.

        Args:
            data: DisplayData to render
            title: Optional title to display above frame

        Returns:
            Colored ASCII art with optional title
        """
        lines = []

        if title:
            lines.append("")
            lines.append(title.center(self.width))
            lines.append("=" * self.width)

        lines.append(self.render(data))

        return "\n".join(lines)
