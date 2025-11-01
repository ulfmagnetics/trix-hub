"""
ASCII renderer for terminal debugging.

Renders DisplayData as ASCII art for terminal output, useful for
testing and debugging without needing the actual LED matrix hardware.
"""

from trixhub.providers.base import DisplayData
from trixhub.renderers.base import Renderer


class ASCIIRenderer(Renderer):
    """
    Renders DisplayData as ASCII art for terminal display.

    Creates a box-drawing representation suitable for terminal output.
    Useful for testing providers and data flow without hardware.
    """

    def __init__(self, width: int = 64, height: int = 16):
        """
        Initialize ASCII renderer.

        Args:
            width: Display width in characters (default: 64)
            height: Display height in lines (default: 16)
        """
        self.width = width
        self.height = height

    def render(self, data: DisplayData) -> str:
        """
        Render DisplayData to ASCII art string.

        Args:
            data: Structured data from a provider

        Returns:
            Multi-line ASCII art string

        Raises:
            ValueError: If content type is not supported
        """
        content_type = data.content.get("type")

        if content_type == "time":
            return self._render_time(data)
        else:
            return self._render_error(f"Unknown type: {content_type}")

    def _render_time(self, data: DisplayData) -> str:
        """
        Render time display as ASCII art.

        Creates a bordered box with centered time and date at bottom.

        Args:
            data: DisplayData with time information

        Returns:
            ASCII art representation
        """
        output = []

        # Top border
        output.append("+" + "-" * (self.width - 2) + "+")

        # Get time and date strings
        time_str = data.content.get("time_12h", "??:??")
        date_str = data.content.get("date", "")

        # Calculate centering for time
        time_padding = (self.width - len(time_str) - 2) // 2
        time_line = "|" + " " * time_padding + time_str
        time_line += " " * (self.width - len(time_line) - 1) + "|"
        output.append(time_line)

        # Add blank lines (leave room for date at bottom)
        for _ in range(self.height - 4):
            output.append("|" + " " * (self.width - 2) + "|")

        # Date at bottom
        date_line = "|" + date_str.ljust(self.width - 2) + "|"
        output.append(date_line)

        # Bottom border
        output.append("+" + "-" * (self.width - 2) + "+")

        return "\n".join(output)

    def _render_error(self, message: str) -> str:
        """
        Render error message as ASCII.

        Args:
            message: Error message to display

        Returns:
            ASCII art error representation
        """
        output = []

        # Top border (use different characters for errors)
        output.append("!" + "=" * (self.width - 2) + "!")

        # Error header
        header = "! ERROR !".center(self.width - 2)
        output.append("!" + header + "!")

        # Blank line
        output.append("!" + " " * (self.width - 2) + "!")

        # Error message (word wrap if needed)
        words = message.split()
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word

            if len(test_line) <= self.width - 4:
                current_line = test_line
            else:
                if current_line:
                    line = "! " + current_line.ljust(self.width - 4) + " !"
                    output.append(line)
                current_line = word

        # Add final line
        if current_line:
            line = "! " + current_line.ljust(self.width - 4) + " !"
            output.append(line)

        # Fill remaining height
        while len(output) < self.height:
            output.append("!" + " " * (self.width - 2) + "!")

        # Bottom border
        output.append("!" + "=" * (self.width - 2) + "!")

        return "\n".join(output[:self.height])

    def render_frame(self, data: DisplayData, title: str = None) -> str:
        """
        Render with optional title above the frame.

        Useful for debugging multiple providers.

        Args:
            data: DisplayData to render
            title: Optional title to display above frame

        Returns:
            ASCII art with optional title
        """
        lines = []

        if title:
            lines.append("")
            lines.append(title.center(self.width))
            lines.append("=" * self.width)

        lines.append(self.render(data))

        return "\n".join(lines)
