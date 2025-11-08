"""
Weather icon renderer for pixel bitmaps.

Creates simple geometric weather icons suitable for LED matrix display.
Supports 12x12 and 14x14 sizes.
"""

from PIL import Image, ImageDraw


def draw_weather_icon(condition: str, size: int = 12) -> Image.Image:
    """
    Draw a weather icon for the given condition.

    Args:
        condition: Weather condition (sunny, cloudy, rainy, etc.)
        size: Icon size in pixels (12 or 14)

    Returns:
        PIL Image with weather icon
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
    return renderer(size)


def draw_sunny_icon(size: int = 12) -> Image.Image:
    """Draw sunny weather icon (yellow circle with rays)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    if size == 14:
        # Yellow sun circle
        draw.ellipse([4, 4, 10, 10], fill=(255, 255, 0))
        # Sun rays
        ray_color = (255, 200, 0)
        draw.point([1, 1], fill=ray_color)
        draw.point([12, 1], fill=ray_color)
        draw.point([1, 12], fill=ray_color)
        draw.point([12, 12], fill=ray_color)
        draw.point([7, 0], fill=ray_color)
        draw.point([0, 7], fill=ray_color)
        draw.point([13, 7], fill=ray_color)
        draw.point([7, 13], fill=ray_color)
    else:  # 12x12
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


def draw_partly_cloudy_icon(size: int = 12) -> Image.Image:
    """Draw partly cloudy icon (sun + small cloud)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    cloud_color = (200, 200, 200)

    if size == 14:
        # Small sun (top-left)
        draw.ellipse([1, 1, 7, 7], fill=(255, 255, 0))
        # Small cloud (bottom-right)
        draw.ellipse([6, 7, 12, 12], fill=cloud_color)
        draw.ellipse([7, 8, 13, 13], fill=cloud_color)
    else:  # 12x12
        # Small sun (top-left)
        draw.ellipse([1, 1, 6, 6], fill=(255, 255, 0))
        # Small cloud (bottom-right)
        draw.ellipse([5, 6, 10, 10], fill=cloud_color)
        draw.ellipse([6, 7, 11, 11], fill=cloud_color)

    return img


def draw_cloudy_icon(size: int = 12) -> Image.Image:
    """Draw cloudy weather icon (gray cloud shape)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    cloud_color = (180, 180, 180)

    if size == 14:
        # Cloud shape (overlapping circles)
        draw.ellipse([1, 5, 8, 11], fill=cloud_color)  # Left bump
        draw.ellipse([6, 4, 13, 10], fill=cloud_color)  # Right bump
        draw.ellipse([3, 6, 11, 13], fill=cloud_color)  # Bottom
    else:  # 12x12
        # Cloud shape (overlapping circles)
        draw.ellipse([1, 4, 7, 10], fill=cloud_color)  # Left bump
        draw.ellipse([5, 3, 11, 9], fill=cloud_color)  # Right bump
        draw.ellipse([3, 5, 9, 11], fill=cloud_color)  # Bottom

    return img


def draw_rainy_icon(size: int = 12) -> Image.Image:
    """Draw rainy weather icon (cloud + rain lines)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    cloud_color = (160, 160, 160)
    rain_color = (100, 150, 255)

    if size == 14:
        # Cloud (top)
        draw.ellipse([1, 1, 8, 6], fill=cloud_color)
        draw.ellipse([5, 2, 12, 7], fill=cloud_color)
        # Rain lines (blue)
        draw.line([2, 8, 2, 12], fill=rain_color)
        draw.line([6, 9, 6, 13], fill=rain_color)
        draw.line([10, 8, 10, 12], fill=rain_color)
    else:  # 12x12
        # Cloud (top)
        draw.ellipse([1, 1, 7, 5], fill=cloud_color)
        draw.ellipse([4, 2, 10, 6], fill=cloud_color)
        # Rain lines (blue)
        draw.line([2, 7, 2, 10], fill=rain_color)
        draw.line([5, 8, 5, 11], fill=rain_color)
        draw.line([8, 7, 8, 10], fill=rain_color)

    return img


def draw_snowy_icon(size: int = 12) -> Image.Image:
    """Draw snowy weather icon (cloud + snowflakes)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    cloud_color = (180, 180, 180)
    snow_color = (255, 255, 255)

    if size == 14:
        # Cloud (top)
        draw.ellipse([1, 1, 8, 6], fill=cloud_color)
        draw.ellipse([5, 2, 12, 7], fill=cloud_color)
        # Snowflakes (white asterisks)
        # Snowflake 1
        draw.point([2, 9], fill=snow_color)
        draw.point([1, 10], fill=snow_color)
        draw.point([3, 10], fill=snow_color)
        # Snowflake 2
        draw.point([7, 10], fill=snow_color)
        draw.point([6, 11], fill=snow_color)
        draw.point([8, 11], fill=snow_color)
        # Snowflake 3
        draw.point([11, 9], fill=snow_color)
        draw.point([10, 10], fill=snow_color)
        draw.point([12, 10], fill=snow_color)
    else:  # 12x12
        # Cloud (top)
        draw.ellipse([1, 1, 7, 5], fill=cloud_color)
        draw.ellipse([4, 2, 10, 6], fill=cloud_color)
        # Snowflakes (white asterisks)
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


def draw_thunderstorm_icon(size: int = 12) -> Image.Image:
    """Draw thunderstorm icon (cloud + lightning bolt)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    cloud_color = (120, 120, 120)
    lightning_color = (255, 255, 0)

    if size == 14:
        # Cloud (top)
        draw.ellipse([1, 1, 8, 6], fill=cloud_color)
        draw.ellipse([5, 2, 12, 7], fill=cloud_color)
        # Lightning bolt (yellow zigzag)
        draw.line([7, 7, 6, 9], fill=lightning_color)
        draw.line([6, 9, 8, 10], fill=lightning_color)
        draw.line([8, 10, 6, 13], fill=lightning_color)
    else:  # 12x12
        # Cloud (top)
        draw.ellipse([1, 1, 7, 5], fill=cloud_color)
        draw.ellipse([4, 2, 10, 6], fill=cloud_color)
        # Lightning bolt (yellow zigzag)
        draw.line([6, 6, 5, 8], fill=lightning_color)
        draw.line([5, 8, 7, 9], fill=lightning_color)
        draw.line([7, 9, 5, 11], fill=lightning_color)

    return img


def draw_windy_icon(size: int = 12) -> Image.Image:
    """Draw windy weather icon (curved lines)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    wind_color = (200, 200, 200)

    if size == 14:
        # Top wind line
        draw.line([1, 4, 11, 4], fill=wind_color)
        draw.line([11, 4, 12, 5], fill=wind_color)
        # Middle wind line
        draw.line([0, 7, 10, 7], fill=wind_color)
        draw.line([10, 7, 11, 8], fill=wind_color)
        # Bottom wind line
        draw.line([2, 10, 13, 10], fill=wind_color)
    else:  # 12x12
        # Top wind line
        draw.line([1, 3, 10, 3], fill=wind_color)
        draw.line([10, 3, 11, 4], fill=wind_color)
        # Middle wind line
        draw.line([0, 6, 9, 6], fill=wind_color)
        draw.line([9, 6, 10, 7], fill=wind_color)
        # Bottom wind line
        draw.line([2, 9, 11, 9], fill=wind_color)

    return img


def draw_error_icon(size: int = 12) -> Image.Image:
    """Draw error icon (sad face or X)."""
    img = Image.new('RGB', (size, size), color='black')
    draw = ImageDraw.Draw(img)

    error_color = (255, 0, 0)

    if size == 14:
        # Red X
        draw.line([2, 2, 12, 12], fill=error_color, width=2)
        draw.line([12, 2, 2, 12], fill=error_color, width=2)
    else:  # 12x12
        # Red X
        draw.line([2, 2, 10, 10], fill=error_color, width=2)
        draw.line([10, 2, 2, 10], fill=error_color, width=2)

    return img
