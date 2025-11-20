"""
S3 Image Provider for trix-hub.

Fetches random images from an S3 bucket and displays them on the LED matrix.
Cycles through all images before repeating (list, randomize, iterate, repeat).
"""

import os
import random
import io
from datetime import datetime, timedelta
from typing import Optional, List

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from PIL import Image

from trixhub.providers.base import DataProvider, DisplayData


# Supported image extensions (lowercase)
SUPPORTED_EXTENSIONS = {'.bmp', '.jpg', '.jpeg', '.png', '.gif', '.webp'}


class S3ImageProvider(DataProvider):
    """
    Provider that fetches images from an S3 bucket.

    Cycles through all images in random order before repeating.
    Supports automatic format conversion and resizing to 64x32.
    """

    def __init__(self, config_key: str = "s3_image", quiet: bool = False):
        """
        Initialize S3 image provider.

        Args:
            config_key: Key in config.json providers section (default: "s3_image")
            quiet: If True, reduce logging output to minimize SD card wear
        """
        super().__init__()

        self.quiet = quiet

        # Load configuration
        from trixhub.config import get_config
        self.config = get_config().get_provider_config(config_key)

        # Load conditions for conditional execution (e.g., birthdays, holidays)
        self._load_conditions(self.config)

        # S3 configuration
        self.bucket_name = self.config.get("s3_bucket")
        self.prefix = self.config.get("s3_prefix", "")
        self.region = self.config.get("aws_region", os.environ.get("AWS_REGION", "us-east-1"))

        # Display configuration
        self.target_width = 64
        self.target_height = 32

        # State for cycling through images
        self._image_keys: List[str] = []
        self._current_index: int = 0

        # Initialize S3 client
        self._init_s3_client()

        # Initial bucket listing
        self._refresh_image_list()

    def _init_s3_client(self):
        """
        Initialize boto3 S3 client with credentials from env vars or config.

        Preference order:
        1. AWS environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        2. Config.json credentials
        """
        # Try environment variables first
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

        # Fall back to config if env vars not set
        if not aws_access_key or not aws_secret_key:
            aws_access_key = self.config.get("aws_access_key_id")
            aws_secret_key = self.config.get("aws_secret_access_key")

        try:
            if aws_access_key and aws_secret_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=self.region
                )
            else:
                # Use default credential chain (IAM role, etc.)
                self.s3_client = boto3.client('s3', region_name=self.region)

            if not self.quiet:
                print(f"[S3ImageProvider] Initialized S3 client for bucket: {self.bucket_name}")

        except NoCredentialsError:
            print("[S3ImageProvider] ERROR: No AWS credentials found")
            self.s3_client = None
        except Exception as e:
            print(f"[S3ImageProvider] ERROR: Failed to initialize S3 client: {e}")
            self.s3_client = None

    def _is_supported_image(self, key: str) -> bool:
        """
        Check if S3 object key has a supported image extension.

        Args:
            key: S3 object key

        Returns:
            True if extension is supported
        """
        # Get extension (lowercase)
        ext = os.path.splitext(key)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    def _refresh_image_list(self):
        """
        List S3 bucket contents, filter by image extensions, and randomize order.
        """
        if not self.s3_client or not self.bucket_name:
            print("[S3ImageProvider] Cannot refresh image list: S3 client not initialized or bucket not specified")
            self._image_keys = []
            return

        try:
            if not self.quiet:
                print(f"[S3ImageProvider] Listing bucket: {self.bucket_name} (prefix: {self.prefix or '(none)'})")

            # List objects in bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)

            # Collect image keys
            image_keys = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # Skip directories (keys ending with /)
                        if not key.endswith('/') and self._is_supported_image(key):
                            image_keys.append(key)

            # Randomize order
            random.shuffle(image_keys)

            self._image_keys = image_keys
            self._current_index = 0

            if not self.quiet:
                print(f"[S3ImageProvider] Found {len(self._image_keys)} images in bucket")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            print(f"[S3ImageProvider] ERROR: Failed to list bucket: {error_code} - {e}")
            self._image_keys = []
        except Exception as e:
            print(f"[S3ImageProvider] ERROR: Failed to list bucket: {e}")
            self._image_keys = []

    def _fetch_image_from_s3(self, key: str) -> Optional[Image.Image]:
        """
        Fetch image from S3 and load it with PIL.

        Args:
            key: S3 object key

        Returns:
            PIL Image object, or None if fetch/load fails
        """
        if not self.s3_client:
            return None

        try:
            # Fetch object from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            image_data = response['Body'].read()

            # Load with PIL
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB mode (required for BMP output)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            return image

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            print(f"[S3ImageProvider] ERROR: Failed to fetch {key}: {error_code} - {e}")
            return None
        except Exception as e:
            print(f"[S3ImageProvider] ERROR: Failed to load image {key}: {e}")
            return None

    def _resize_image(self, image: Image.Image) -> Image.Image:
        """
        Resize/crop image to fit target dimensions (64x32).

        Strategy:
        - If image is already 64x32, return as-is
        - Otherwise, resize maintaining aspect ratio and crop from center

        Args:
            image: PIL Image object

        Returns:
            Resized/cropped PIL Image (64x32)
        """
        width, height = image.size

        # Already correct size
        if width == self.target_width and height == self.target_height:
            return image

        # Calculate aspect ratios
        target_ratio = self.target_width / self.target_height
        image_ratio = width / height

        # Resize to cover target dimensions (may be larger in one dimension)
        if image_ratio > target_ratio:
            # Image is wider - resize by height
            new_height = self.target_height
            new_width = int(width * (new_height / height))
        else:
            # Image is taller - resize by width
            new_width = self.target_width
            new_height = int(height * (new_width / width))

        # Resize with high-quality resampling
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Crop from center to exact target dimensions
        left = (new_width - self.target_width) // 2
        top = (new_height - self.target_height) // 2
        right = left + self.target_width
        bottom = top + self.target_height

        image = image.crop((left, top, right, bottom))

        return image

    def fetch_data(self) -> DisplayData:
        """
        Fetch next image in cycle from S3.

        Returns:
            DisplayData with PIL Image in content, or error if no images available
        """
        # Check if we need to refresh the image list
        if not self._image_keys or self._current_index >= len(self._image_keys):
            self._refresh_image_list()

        # Still no images after refresh
        if not self._image_keys:
            return DisplayData(
                timestamp=datetime.now(),
                content={
                    "type": "s3_image",
                    "error": True,
                    "error_message": "No images found in S3 bucket"
                },
                metadata={
                    "priority": "normal",
                    "suggested_display_duration": 10
                }
            )

        # Get next image key
        key = self._image_keys[self._current_index]
        self._current_index += 1

        if not self.quiet:
            print(f"[S3ImageProvider] Fetching image {self._current_index}/{len(self._image_keys)}: {key}")

        # Fetch and process image
        image = self._fetch_image_from_s3(key)

        if image is None:
            # Failed to fetch/load this image - try next one on next cycle
            return DisplayData(
                timestamp=datetime.now(),
                content={
                    "type": "s3_image",
                    "error": True,
                    "error_message": f"Failed to load image: {key}"
                },
                metadata={
                    "priority": "normal",
                    "suggested_display_duration": 5
                }
            )

        # Resize/crop to target dimensions
        image = self._resize_image(image)

        # Return DisplayData with image
        return DisplayData(
            timestamp=datetime.now(),
            content={
                "type": "s3_image",
                "image": image,
                "image_key": key,
                "bucket": self.bucket_name,
                "image_number": self._current_index,
                "total_images": len(self._image_keys)
            },
            metadata={
                "priority": "normal",
                "suggested_display_duration": 30
            }
        )

    def get_cache_duration(self) -> timedelta:
        """
        No caching - advance to next image on each fetch.

        Returns:
            0 seconds (no caching)
        """
        return timedelta(seconds=0)
