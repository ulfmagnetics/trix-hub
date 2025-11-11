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
        elif content_type == "bus_arrivals":
            return self._render_bus_arrivals(data)
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
        - Top row (0-11px): 3 weather icons (12x12) - current, +3h, +6h
        - Middle row (12-20px): time labels (font size 7) - "Now", "3p", "6p"
        - Bottom row (22-31px): temp left, AQI center (color-coded), wind right (font size 8)

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

        # Load fonts (reduced to size 8 to fit temp + AQI + wind)
        if self.font_path:
            text_font = ImageFont.truetype(self.font_path, 8)
        else:
            text_font = ImageFont.load_default()

        # Get weather data
        current = data.content.get("current", {})
        forecast1 = data.content.get("forecast1", {})
        forecast2 = data.content.get("forecast2", {})

        current_temp = current.get("temperature", 0)
        current_condition = current.get("condition", "cloudy")
        current_windspeed = current.get("windspeed", 0)
        current_wind_direction = current.get("wind_direction", 0)
        current_time_label = current.get("time_label", "Now")
        current_aqi = current.get("aqi")

        forecast1_condition = forecast1.get("condition", "cloudy")
        forecast1_time_label = forecast1.get("time_label", "")

        forecast2_condition = forecast2.get("condition", "cloudy")
        forecast2_time_label = forecast2.get("time_label", "")

        # Convert wind direction to arrow
        # Wind direction in degrees: 0=N, 90=E, 180=S, 270=W
        # Arrow shows where wind is coming FROM (weathervane style)
        def wind_direction_to_arrow(degrees):
            """Convert wind direction in degrees to arrow character."""
            # Normalize to 0-360
            degrees = degrees % 360

            # Map to 8 directions with arrows showing where wind comes FROM
            if degrees < 22.5 or degrees >= 337.5:
                return "↑"  # North wind (from North)
            elif degrees < 67.5:
                return "↗"  # Northeast wind
            elif degrees < 112.5:
                return "→"  # East wind (from East)
            elif degrees < 157.5:
                return "↘"  # Southeast wind
            elif degrees < 202.5:
                return "↓"  # South wind (from South)
            elif degrees < 247.5:
                return "↙"  # Southwest wind
            elif degrees < 292.5:
                return "←"  # West wind (from West)
            else:
                return "↖"  # Northwest wind

        def aqi_to_color(aqi):
            """Convert AQI value to US standard color."""
            if aqi is None:
                return (128, 128, 128)  # Gray for unavailable
            elif aqi <= 50:
                return (0, 228, 0)  # Green - Good
            elif aqi <= 100:
                return (255, 255, 0)  # Yellow - Moderate
            elif aqi <= 150:
                return (255, 126, 0)  # Orange - Unhealthy for Sensitive
            elif aqi <= 200:
                return (255, 0, 0)  # Red - Unhealthy
            elif aqi <= 300:
                return (143, 63, 151)  # Purple - Very Unhealthy
            else:
                return (126, 0, 35)  # Maroon - Hazardous

        wind_arrow = wind_direction_to_arrow(current_wind_direction)

        # Top row: 3 weather icons (12x12)
        # Icon spacing: centered in ~21px segments
        icon1_x = 5   # Centered in first 21px
        icon2_x = 26  # Centered in middle 21px
        icon3_x = 47  # Centered in last 21px
        icon_y = 0

        # Draw icons
        current_icon = draw_weather_icon(current_condition, size=12)
        img.paste(current_icon, (icon1_x, icon_y))

        forecast1_icon = draw_weather_icon(forecast1_condition, size=12)
        img.paste(forecast1_icon, (icon2_x, icon_y))

        forecast2_icon = draw_weather_icon(forecast2_condition, size=12)
        img.paste(forecast2_icon, (icon3_x, icon_y))

        # Middle row: time labels (font size 7)
        if self.font_path:
            time_font = ImageFont.truetype(self.font_path, 7)
        else:
            time_font = ImageFont.load_default()

        time_y = 12

        # Center each time label under its icon
        # Icon 1 time label
        time1_width = draw.textlength(current_time_label, font=time_font)
        time1_x = icon1_x + (12 - time1_width) // 2
        draw.text((time1_x, time_y), current_time_label, fill='white', font=time_font)

        # Icon 2 time label
        time2_width = draw.textlength(forecast1_time_label, font=time_font)
        time2_x = icon2_x + (12 - time2_width) // 2
        draw.text((time2_x, time_y), forecast1_time_label, fill='white', font=time_font)

        # Icon 3 time label
        time3_width = draw.textlength(forecast2_time_label, font=time_font)
        time3_x = icon3_x + (12 - time3_width) // 2
        draw.text((time3_x, time_y), forecast2_time_label, fill='white', font=time_font)

        # Bottom row: temperature (left), AQI (middle), wind (right)
        text_y = 22

        # Temperature on left (no unit label)
        temp_text = f"{current_temp}°"
        draw.text((2, text_y), temp_text, fill='white', font=text_font)

        # AQI in middle (color-coded)
        if current_aqi is not None:
            aqi_text = str(current_aqi)
            aqi_color = aqi_to_color(current_aqi)
            aqi_width = draw.textlength(aqi_text, font=text_font)
            aqi_x = (self.width - aqi_width) // 2  # Centered
            draw.text((aqi_x, text_y), aqi_text, fill=aqi_color, font=text_font)

        # Wind on right (arrow + speed)
        wind_text = f"{wind_arrow}{current_windspeed}"
        wind_width = draw.textlength(wind_text, font=text_font)
        wind_x = self.width - wind_width - 2
        draw.text((wind_x, text_y), wind_text, fill='white', font=text_font)

        return img

    def _render_bus_arrivals(self, data: DisplayData) -> Image.Image:
        """
        Render bus arrivals display.

        Layout:
        - 4 rows of arrivals (8 pixels each = 32 total)
        - Format: "67 5 mins" (realtime) or "67 5 mins*" (scheduled)
        - Asterisk indicates scheduled time without vehicle data
        - Color-coded by urgency:
          - Red: <5 minutes (urgent)
          - Yellow: 5-10 minutes (soon)
          - Green: 10+ minutes (normal)

        Args:
            data: DisplayData with bus arrival information

        Returns:
            Rendered PIL Image
        """
        # Create black background
        img = Image.new('RGB', (self.width, self.height), color='black')
        draw = ImageDraw.Draw(img)

        # Check for error condition
        if data.content.get("error"):
            error_msg = data.content.get("error_message", "Bus data error")

            # Load font
            if self.font_path:
                font = ImageFont.truetype(self.font_path, 8)
            else:
                font = ImageFont.load_default()

            # Draw error message centered
            x, y = center_text(error_msg, font, self.width, self.height)
            draw.text((x, y), error_msg, fill='red', font=font)

            return img

        # Load font (size 8 for compact display)
        if self.font_path:
            font = ImageFont.truetype(self.font_path, 8)
        else:
            font = ImageFont.load_default()

        # Get arrivals
        arrivals = data.content.get("arrivals", [])

        # Define urgency colors
        urgency_colors = {
            'urgent': (255, 0, 0),      # Red (<5 mins)
            'soon': (255, 255, 0),      # Yellow (5-10 mins)
            'normal': (0, 255, 0),      # Green (10+ mins)
        }

        # Render each arrival (max 4 rows)
        y_offset = 0
        line_height = 8

        for i, arrival in enumerate(arrivals[:4]):  # Max 4 arrivals
            # Extract data
            route = arrival.get('route_short_name', '??')
            minutes = arrival.get('minutes_until', 0)
            arrival_type = arrival.get('type', 'SC')  # TT or SC
            urgency = arrival.get('urgency', 'normal')

            # Get color based on urgency
            color = urgency_colors.get(urgency, (255, 255, 255))

            # Format: "67 5 mins" or "67 5 mins*"
            # Build text components
            route_text = str(route)

            # Format minutes
            if minutes == 0:
                time_text = "NOW"
            elif minutes == 1:
                time_text = "1 min"
            else:
                time_text = f"{minutes} mins"

            # Add asterisk for scheduled (SC) arrivals only
            if arrival_type == 'SC':
                time_text += '*'

            # Build full line
            # Layout: "67" on left, "5 mins" or "5 mins*" on right
            left_text = route_text
            right_text = time_text

            # Draw left text (route number)
            draw.text((2, y_offset), left_text, fill=color, font=font)

            # Draw right text (time with optional asterisk) - right-aligned
            right_width = draw.textlength(right_text, font=font)
            right_x = self.width - right_width - 2
            draw.text((right_x, y_offset), right_text, fill=color, font=font)

            y_offset += line_height

        # If no arrivals, show message
        if not arrivals:
            no_arrivals_msg = "No arrivals"
            x, y = center_text(no_arrivals_msg, font, self.width, self.height)
            draw.text((x, y), no_arrivals_msg, fill='white', font=font)

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
