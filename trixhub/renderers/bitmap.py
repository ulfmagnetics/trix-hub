"""
Bitmap renderer for LED matrix displays.

Renders DisplayData to PIL Image objects suitable for 64x32 RGB LED matrices.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from trixhub.providers.base import DisplayData
from trixhub.renderers.base import Renderer
from trixhub.renderers.weather_icons import draw_weather_icon
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
        elif content_type == "weather":
            return self._render_weather(data)
        else:
            return self._render_error(f"Unknown type: {content_type}")

    def _render_time(self, data: DisplayData) -> Image.Image:
        """
        Render time display with border and padding.

        Shows time at top in ROYGBIV rainbow colors, date at bottom right-aligned,
        with 1px grey border and 2px padding.

        Args:
            data: DisplayData with time information

        Returns:
            Rendered PIL Image
        """
        # Create black background
        img = Image.new('RGB', (self.width, self.height), color='black')
        draw = ImageDraw.Draw(img)

        # Draw 1-pixel grey border
        border_color = (128, 128, 128)
        draw.rectangle(
            [(0, 0), (self.width - 1, self.height - 1)],
            outline=border_color,
            width=1
        )

        # Define content area (1px border + 2px padding = 3px offset on each side)
        content_x = 3
        content_y = 3
        content_width = self.width - 6  # 58 pixels
        content_height = self.height - 6  # 26 pixels
        content_right = self.width - 3  # 61
        content_bottom = self.height - 3  # 29

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

        # Calculate time width for centering
        time_width = draw.textlength(time_str, font=time_font)
        time_x = content_x + (content_width - time_width) // 2
        time_y = content_y + 2  # Near top of content area

        # Draw each character in a different color (skip spaces)
        current_x = time_x
        color_index = 0
        for char in time_str:
            # Skip spaces for color assignment
            if char == ' ':
                color = (0, 0, 0)  # Black (invisible on black background)
            else:
                color = rainbow_colors[color_index % len(rainbow_colors)]
                color_index += 1

            draw.text((current_x, time_y), char, fill=color, font=time_font)

            # Move to next character position
            char_width = draw.textlength(char, font=time_font)
            current_x += char_width

        # Add date at bottom, right-aligned
        date_str = data.content.get("date_us", "")
        if date_str:
            date_width = draw.textlength(date_str, font=date_font)
            date_x = content_right - date_width
            date_y = content_bottom - 10  # 10 pixels from bottom of content area
            draw.text((date_x, date_y), date_str, fill=(128, 128, 128), font=date_font)

        return img

    def _render_weather(self, data: DisplayData) -> Image.Image:
        """
        Render weather display.

        Layout:
        - Top row (14px): 3 weather icons (14x14) - current, +3h, +6h
        - Bottom row (18px): temperature left, wind speed right

        Args:
            data: DisplayData with weather information

        Returns:
            Rendered PIL Image
        """
        # Create black background (no border/padding for weather)
        img = Image.new('RGB', (self.width, self.height), color='black')
        draw = ImageDraw.Draw(img)

        # Check for error condition
        if data.content.get("error"):
            error_msg = data.content.get("error_message", "Weather API error 😢")

            # Load font
            if self.font_path:
                font = ImageFont.truetype(self.font_path, 10)
            else:
                font = ImageFont.load_default()

            # Draw error message centered
            x, y = center_text(error_msg, font, self.width, self.height)
            draw.text((x, y), error_msg, fill='red', font=font)

            return img

        # Load fonts
        if self.font_path:
            text_font = ImageFont.truetype(self.font_path, 10)
        else:
            text_font = ImageFont.load_default()

        # Get weather data
        current = data.content.get("current", {})
        forecast1 = data.content.get("forecast1", {})
        forecast2 = data.content.get("forecast2", {})

        current_temp = current.get("temperature", 0)
        current_condition = current.get("condition", "cloudy")
        current_windspeed = current.get("windspeed", 0)
        current_units = current.get("units", "fahrenheit")

        forecast1_condition = forecast1.get("condition", "cloudy")
        forecast2_condition = forecast2.get("condition", "cloudy")

        # Unit symbol
        unit_symbol = "°F" if current_units == "fahrenheit" else "°C"

        # Top row: 3 weather icons (14x14)
        # Icon spacing: 4px gap between icons
        icon1_x = 4
        icon2_x = 25  # 4 + 14 + 7
        icon3_x = 46  # 25 + 14 + 7
        icon_y = 0

        # Draw icons
        current_icon = draw_weather_icon(current_condition, size=14)
        img.paste(current_icon, (icon1_x, icon_y))

        forecast1_icon = draw_weather_icon(forecast1_condition, size=14)
        img.paste(forecast1_icon, (icon2_x, icon_y))

        forecast2_icon = draw_weather_icon(forecast2_condition, size=14)
        img.paste(forecast2_icon, (icon3_x, icon_y))

        # Bottom row: temperature (left) and wind speed (right)
        text_y = 18  # Centered in bottom 18px area

        # Temperature on left
        temp_text = f"{current_temp}{unit_symbol}"
        draw.text((2, text_y), temp_text, fill='white', font=text_font)

        # Wind speed on right
        wind_text = f"{current_windspeed}mph"
        wind_width = draw.textlength(wind_text, font=text_font)
        wind_x = self.width - wind_width - 2
        draw.text((wind_x, text_y), wind_text, fill='white', font=text_font)

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
