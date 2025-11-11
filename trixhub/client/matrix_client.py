"""
Matrix Portal HTTP client.

Handles communication with trix-server (MatrixPortal M4) via HTTP POST.
"""

import io
import os
from datetime import datetime
from PIL import Image
import requests



class MatrixClient:
    """
    Client for posting bitmaps to Matrix Portal via HTTP.

    Posts BMP-formatted images to trix-server running on MatrixPortal M4.
    """

    DISPLAY_ENDPOINT = "/display"
    CLEAR_ENDPOINT = "/clear"

    def __init__(self, server_hostname: str, width: int = 64, height: int = 32,
                 output_dir: str = "output", timeout: int = 5, save_debug_files: bool = False):
        """
        Initialize Matrix Portal client.

        Args:
            server_hostname: Hostname or base URL of trix-server (e.g., http://192.168.1.XX or http://trix-server.local)
            width: Expected bitmap width (default: 64)
            height: Expected bitmap height (default: 32)
            output_dir: Directory to save debug bitmap files (only used if save_debug_files=True)
            timeout: HTTP request timeout in seconds (default: 5)
            save_debug_files: If True, save bitmap files locally for debugging (default: False)
        """
        self.server_hostname = server_hostname.rstrip('/')
        self.width = width
        self.height = height
        self.output_dir = output_dir
        self.timeout = timeout
        self.save_debug_files = save_debug_files

        # Create output directory if debug mode enabled
        if save_debug_files and not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def post_bitmap(self, image: Image.Image) -> bool:
        """
        Post bitmap to Matrix Portal via HTTP POST.

        Args:
            image: PIL Image to send (should be width x height RGB)

        Returns:
            True if successful, False otherwise
        """
        url = self.server_hostname + self.DISPLAY_ENDPOINT
        try:
            # Validate image size
            if image.size != (self.width, self.height):
                print(f"[MatrixClient] Warning: Image size {image.size} doesn't match expected {(self.width, self.height)}")

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert image to BMP bytes
            bmp_bytes = self._image_to_bmp_bytes(image)

            # POST to trix-server
            response = requests.post(
                url,
                data=bmp_bytes,
                headers={'Content-Type': 'image/bmp'},
                timeout=self.timeout
            )

            # Check response
            if response.status_code == 200:
                # Optionally save debug file
                if self.save_debug_files:
                    self._save_debug_file(image)
                return True
            else:
                print(f"[MatrixClient] HTTP {response.status_code}: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print(f"[MatrixClient] Timeout connecting to {url}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[MatrixClient] Connection error: {url} unreachable")
            return False
        except Exception as e:
            print(f"[MatrixClient] Error: {e}")
            return False

    def clear_display(self) -> bool:
        """
        Clear the Matrix Portal display by sending a GET to the /clear endpoint.
        Returns:
            True if successful, False otherwise
        """
        url = self.server_hostname + self.CLEAR_ENDPOINT
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return True
            else:
                print(f"[MatrixClient] Clear display HTTP {response.status_code}: {response.text}")
                return False
        except requests.exceptions.Timeout:
            print(f"[MatrixClient] Timeout connecting to {url}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[MatrixClient] Connection error: {url} unreachable")
            return False
        except Exception as e:
            print(f"[MatrixClient] Error clearing display: {e}")
            return False

    def _image_to_bmp_bytes(self, image: Image.Image) -> bytes:
        """
        Convert PIL Image to BMP format bytes.

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

    def _save_debug_file(self, image: Image.Image) -> None:
        """
        Save bitmap to file for debugging purposes.

        Args:
            image: PIL Image to save
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/matrix_{timestamp}.bmp"
        image.save(filename, format='BMP')
        print(f"[MatrixClient] Debug: Saved bitmap to {filename}")

    def test_connection(self) -> bool:
        """
        Test connection to trix-server.

        Returns:
            True if server is reachable, False otherwise
        """
        try:
            response = requests.get(
                self.server_hostname,
                timeout=self.timeout
            )
            return response.status_code in [200, 404]  # 404 is ok, means server is up
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            return False
        except Exception:
            return False
