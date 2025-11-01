"""
Matrix Portal HTTP client.

Handles communication with trix-server (MatrixPortal M4) via HTTP POST.
Currently stubbed to save bitmaps to files for testing.
"""

import io
import os
from datetime import datetime
from typing import Optional
from PIL import Image


class MatrixClient:
    """
    Client for posting bitmaps to Matrix Portal via HTTP.

    Currently stubbed to save bitmaps to files for testing.
    Will be updated to POST to trix-server once architecture is validated.
    """

    def __init__(self, server_url: str, width: int = 64, height: int = 32,
                 output_dir: str = "output"):
        """
        Initialize Matrix Portal client.

        Args:
            server_url: URL of trix-server bitmap endpoint (e.g., http://192.168.1.XX/bitmap)
            width: Expected bitmap width (default: 64)
            height: Expected bitmap height (default: 32)
            output_dir: Directory to save bitmap files (stub mode only)
        """
        self.server_url = server_url
        self.width = width
        self.height = height
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def post_bitmap(self, image: Image.Image) -> bool:
        """
        Post bitmap to Matrix Portal.

        Currently saves to file for testing. Will be updated to HTTP POST later.

        Args:
            image: PIL Image to send (should be width x height RGB)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate image size
            if image.size != (self.width, self.height):
                print(f"Warning: Image size {image.size} doesn't match expected {(self.width, self.height)}")

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # TODO: Implement actual HTTP POST to trix-server
            # For now, save to file for testing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/matrix_{timestamp}.bmp"

            image.save(filename, format='BMP')
            print(f"[MatrixClient] Saved bitmap to {filename}")
            print(f"[MatrixClient] TODO: POST to {self.server_url}")

            return True

        except Exception as e:
            print(f"[MatrixClient] Error: {e}")
            return False

    def _image_to_bmp_bytes(self, image: Image.Image) -> bytes:
        """
        Convert PIL Image to BMP format bytes.

        This will be used when implementing actual HTTP POST.

        Args:
            image: PIL Image to convert

        Returns:
            BMP-formatted bytes
        """
        # Ensure RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to BMP bytes
        buffer = io.BytesIO()
        image.save(buffer, format='BMP')
        return buffer.getvalue()

    def test_connection(self) -> bool:
        """
        Test connection to trix-server.

        TODO: Implement when HTTP POST is ready.

        Returns:
            True if server is reachable, False otherwise
        """
        print(f"[MatrixClient] TODO: Implement connection test to {self.server_url}")
        return False

    def post_bitmap_http(self, image: Image.Image) -> bool:
        """
        Post bitmap via HTTP POST (future implementation).

        This is the actual implementation that will POST to trix-server.
        Currently not implemented.

        Args:
            image: PIL Image to send

        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement HTTP POST using requests library
        #
        # Implementation will look something like:
        #
        # import requests
        # bmp_bytes = self._image_to_bmp_bytes(image)
        # response = requests.post(
        #     self.server_url,
        #     data=bmp_bytes,
        #     headers={'Content-Type': 'image/bmp'},
        #     timeout=5
        # )
        # return response.status_code == 200

        raise NotImplementedError("HTTP POST not yet implemented - use post_bitmap() for file-based testing")
