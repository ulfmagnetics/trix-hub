"""
Text rendering helper utilities.

Provides common text operations for renderers like centering,
wrapping, and bounding box calculations.
"""

from typing import Optional
from PIL import ImageDraw, ImageFont


def get_text_bbox(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """
    Get the bounding box size of text.

    Args:
        text: Text to measure
        font: Font to use for measurement

    Returns:
        Tuple of (width, height) in pixels
    """
    # Create a temporary draw object for measurement
    from PIL import Image
    temp_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(temp_img)

    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    return (width, height)


def center_text_x(text: str, font: ImageFont.FreeTypeFont, container_width: int) -> int:
    """
    Calculate x coordinate to center text horizontally.

    Args:
        text: Text to center
        font: Font to use
        container_width: Width of container in pixels

    Returns:
        X coordinate for left edge of text
    """
    text_width, _ = get_text_bbox(text, font)
    return (container_width - text_width) // 2


def center_text_y(text: str, font: ImageFont.FreeTypeFont, container_height: int) -> int:
    """
    Calculate y coordinate to center text vertically.

    Args:
        text: Text to center
        font: Font to use
        container_height: Height of container in pixels

    Returns:
        Y coordinate for top edge of text
    """
    _, text_height = get_text_bbox(text, font)
    return (container_height - text_height) // 2


def center_text(text: str, font: ImageFont.FreeTypeFont,
                container_width: int, container_height: int) -> tuple[int, int]:
    """
    Calculate coordinates to center text both horizontally and vertically.

    Args:
        text: Text to center
        font: Font to use
        container_width: Width of container in pixels
        container_height: Height of container in pixels

    Returns:
        Tuple of (x, y) coordinates for text positioning
    """
    x = center_text_x(text, font, container_width)
    y = center_text_y(text, font, container_height)
    return (x, y)


def wrap_text(text: str, max_width: int, font: ImageFont.FreeTypeFont) -> list[str]:
    """
    Wrap text to fit within a maximum width.

    Uses word-based wrapping - splits on whitespace and wraps whole words.

    Args:
        text: Text to wrap
        max_width: Maximum width in pixels
        font: Font to use for measurement

    Returns:
        List of wrapped lines
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        # Try adding word to current line
        test_line = current_line + (" " if current_line else "") + word
        test_width, _ = get_text_bbox(test_line, font)

        if test_width <= max_width:
            # Word fits, add to current line
            current_line = test_line
        else:
            # Word doesn't fit
            if current_line:
                # Save current line and start new one
                lines.append(current_line)
                current_line = word
            else:
                # Single word is too long, add it anyway
                lines.append(word)

    # Add final line if not empty
    if current_line:
        lines.append(current_line)

    return lines


def truncate_text(text: str, max_width: int, font: ImageFont.FreeTypeFont,
                  ellipsis: str = "...") -> str:
    """
    Truncate text with ellipsis to fit within maximum width.

    Args:
        text: Text to truncate
        max_width: Maximum width in pixels
        font: Font to use
        ellipsis: Ellipsis string to append (default: "...")

    Returns:
        Truncated text with ellipsis if needed
    """
    text_width, _ = get_text_bbox(text, font)

    if text_width <= max_width:
        return text

    # Binary search for the right length
    left, right = 0, len(text)
    result = ""

    while left <= right:
        mid = (left + right) // 2
        test_text = text[:mid] + ellipsis
        test_width, _ = get_text_bbox(test_text, font)

        if test_width <= max_width:
            result = test_text
            left = mid + 1
        else:
            right = mid - 1

    return result if result else ellipsis
