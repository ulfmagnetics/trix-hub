"""
Weather icon renderer for 12x12 pixel bitmaps.

Creates simple geometric weather icons suitable for LED matrix display.
"""

from PIL import Image, ImageDraw


def draw_weather_icon(condition: str) -> Image.Image:
    """
    Draw a 12x12 weather icon for the given condition.

    Args:
        condition: Weather condition (sunny, cloudy, rainy, etc.)

    Returns:
        12x12 PIL Image with weather icon
    """
    icon_renderers = {
        "sunny": draw_sunny_icon,
        "partly_cloudy": draw_partly_cloudy_icon,
        "cloudy": draw_cloudy_icon,
        "rainy": draw_rainy_icon,
        "snowy": draw_snowy_icon,
        "thunderstorm": draw_thunderstorm_icon,
        "windy": draw_windy_icon,
        "error": draw_error_icon,
    }

    renderer = icon_renderers.get(condition, draw_cloudy_icon)
    return renderer()


def draw_sunny_icon() -> Image.Image:
    """Draw sunny weather icon (yellow circle with rays)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Yellow sun circle
    draw.ellipse([3, 3, 9, 9], fill=(255, 255, 0))

    # Sun rays (simple dots at corners)
    ray_color = (255, 200, 0)
    draw.point([1, 1], fill=ray_color)
    draw.point([10, 1], fill=ray_color)
    draw.point([1, 10], fill=ray_color)
    draw.point([10, 10], fill=ray_color)
    draw.point([6, 0], fill=ray_color)
    draw.point([0, 6], fill=ray_color)
    draw.point([11, 6], fill=ray_color)
    draw.point([6, 11], fill=ray_color)

    return img


def draw_partly_cloudy_icon() -> Image.Image:
    """Draw partly cloudy icon (sun + small cloud)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Small sun (top-left)
    draw.ellipse([1, 1, 6, 6], fill=(255, 255, 0))

    # Small cloud (bottom-right)
    cloud_color = (200, 200, 200)
    draw.ellipse([5, 6, 10, 10], fill=cloud_color)
    draw.ellipse([6, 7, 11, 11], fill=cloud_color)

    return img


def draw_cloudy_icon() -> Image.Image:
    """Draw cloudy weather icon (gray cloud shape)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Cloud shape (overlapping circles)
    cloud_color = (180, 180, 180)
    draw.ellipse([1, 4, 7, 10], fill=cloud_color)  # Left bump
    draw.ellipse([5, 3, 11, 9], fill=cloud_color)  # Right bump
    draw.ellipse([3, 5, 9, 11], fill=cloud_color)  # Bottom

    return img


def draw_rainy_icon() -> Image.Image:
    """Draw rainy weather icon (cloud + rain lines)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Cloud (top)
    cloud_color = (160, 160, 160)
    draw.ellipse([1, 1, 7, 5], fill=cloud_color)
    draw.ellipse([4, 2, 10, 6], fill=cloud_color)

    # Rain lines (blue)
    rain_color = (100, 150, 255)
    draw.line([2, 7, 2, 10], fill=rain_color)
    draw.line([5, 8, 5, 11], fill=rain_color)
    draw.line([8, 7, 8, 10], fill=rain_color)

    return img


def draw_snowy_icon() -> Image.Image:
    """Draw snowy weather icon (cloud + snowflakes)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Cloud (top)
    cloud_color = (180, 180, 180)
    draw.ellipse([1, 1, 7, 5], fill=cloud_color)
    draw.ellipse([4, 2, 10, 6], fill=cloud_color)

    # Snowflakes (white asterisks)
    snow_color = (255, 255, 255)
    # Snowflake 1
    draw.point([2, 8], fill=snow_color)
    draw.point([1, 9], fill=snow_color)
    draw.point([3, 9], fill=snow_color)

    # Snowflake 2
    draw.point([6, 9], fill=snow_color)
    draw.point([5, 10], fill=snow_color)
    draw.point([7, 10], fill=snow_color)

    # Snowflake 3
    draw.point([9, 8], fill=snow_color)
    draw.point([8, 9], fill=snow_color)
    draw.point([10, 9], fill=snow_color)

    return img


def draw_thunderstorm_icon() -> Image.Image:
    """Draw thunderstorm icon (cloud + lightning bolt)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Cloud (top)
    cloud_color = (120, 120, 120)
    draw.ellipse([1, 1, 7, 5], fill=cloud_color)
    draw.ellipse([4, 2, 10, 6], fill=cloud_color)

    # Lightning bolt (yellow zigzag)
    lightning_color = (255, 255, 0)
    draw.line([6, 6, 5, 8], fill=lightning_color)
    draw.line([5, 8, 7, 9], fill=lightning_color)
    draw.line([7, 9, 5, 11], fill=lightning_color)

    return img


def draw_windy_icon() -> Image.Image:
    """Draw windy weather icon (curved lines)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Wind lines (curved, light gray)
    wind_color = (200, 200, 200)

    # Top wind line
    draw.line([1, 3, 10, 3], fill=wind_color)
    draw.line([10, 3, 11, 4], fill=wind_color)

    # Middle wind line
    draw.line([0, 6, 9, 6], fill=wind_color)
    draw.line([9, 6, 10, 7], fill=wind_color)

    # Bottom wind line
    draw.line([2, 9, 11, 9], fill=wind_color)

    return img


def draw_error_icon() -> Image.Image:
    """Draw error icon (sad face or X)."""
    img = Image.new('RGB', (12, 12), color='black')
    draw = ImageDraw.Draw(img)

    # Red X
    error_color = (255, 0, 0)
    draw.line([2, 2, 10, 10], fill=error_color, width=2)
    draw.line([10, 2, 2, 10], fill=error_color, width=2)

    # Or simple sad face
    # Eyes
    # draw.point([4, 4], fill=error_color)
    # draw.point([8, 4], fill=error_color)
    # Sad mouth
    # draw.arc([3, 6, 9, 10], start=0, end=180, fill=error_color)

    return img
