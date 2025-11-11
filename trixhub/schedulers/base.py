"""
Base scheduler class for trix-hub.

Provides common functionality for all scheduler modes.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any

from trixhub.config import get_config
from trixhub.providers import TimeProvider, WeatherProvider, BusArrivalProvider, DataProvider
from trixhub.providers.s3_image_provider import S3ImageProvider
from trixhub.renderers import BitmapRenderer, ASCIIRenderer
from trixhub.client import MatrixClient


class BaseScheduler(ABC):
    """
    Abstract base class for schedulers.

    Provides common functionality for provider management, rendering,
    and matrix communication. Subclasses implement specific scheduling logic.
    """

    def __init__(self, debug: bool = False):
        """
        Initialize scheduler with configuration and components.

        Args:
            debug: If True, use ASCII renderer and print to console instead of posting bitmaps
        """
        self.config = get_config()
        self.shutdown_requested = False
        self.debug = debug

        # Load configurations
        self.matrix_config = self.config.get_matrix_config()
        if self.debug:
            print(f"matrix config: {self.matrix_config}")
        self.scheduler_config = self.config.get_scheduler_config()
        if self.debug:
            print(f"scheduler config: {self.scheduler_config}")

        # Initialize client and renderers based on debug mode
        if self.debug:
            # Debug mode: use ASCII renderer
            self.ascii_renderer = ASCIIRenderer(
                width=self.matrix_config.get("width", 64),
                height=self.matrix_config.get("height", 32)
            )
            self.client = None
            self.renderer = None
        else:
            # Normal mode: use bitmap renderer and matrix client
            self.client = MatrixClient(
                server_hostname=self.matrix_config.get("server_hostname", "http://trix-server.local"),
                width=self.matrix_config.get("width", 64),
                height=self.matrix_config.get("height", 32),
                output_dir=self.matrix_config.get("output_dir", "output")
            )
            self.renderer = BitmapRenderer(
                width=self.matrix_config.get("width", 64),
                height=self.matrix_config.get("height", 32)
            )
            self.ascii_renderer = None

        # Initialize providers
        self.providers: Dict[str, DataProvider] = {}
        self._init_providers()

        # Get common scheduler settings
        self.default_duration = self.scheduler_config.get("default_display_duration", 30)

    def _init_providers(self):
        """Initialize all configured providers."""
        # Map of base provider names to classes
        provider_classes = {
            "time": TimeProvider,
            "weather": WeatherProvider,
        }

        # Get provider rotation to know which ones to initialize
        # Subclasses may override which providers to initialize
        rotation = self._get_provider_list()

        for provider_entry in rotation:
            provider_name = provider_entry.get("name")

            # Check if provider is enabled in config
            provider_config = self.config.get_provider_config(provider_name)
            if not provider_config.get("enabled", True):
                print(f"[Scheduler] Warning: Provider '{provider_name}' is in rotation but disabled in config")
                continue

            # Initialize provider
            try:
                # Exact match for base providers
                if provider_name in provider_classes:
                    self.providers[provider_name] = provider_classes[provider_name]()
                    print(f"[Scheduler] Initialized provider: {provider_name}")
                # S3 image provider
                elif provider_name == "s3_image":
                    self.providers[provider_name] = S3ImageProvider(config_key=provider_name)
                    print(f"[Scheduler] Initialized S3 image provider: {provider_name}")
                # Bus providers (name starts with "bus_")
                elif provider_name.startswith("bus_"):
                    self.providers[provider_name] = BusArrivalProvider(config_key=provider_name)
                    print(f"[Scheduler] Initialized bus provider: {provider_name}")
                # Weather providers (name starts with "weather_")
                elif provider_name.startswith("weather_"):
                    self.providers[provider_name] = WeatherProvider(config_key=provider_name)
                    print(f"[Scheduler] Initialized weather provider: {provider_name}")
                else:
                    print(f"[Scheduler] Warning: Unknown provider '{provider_name}' in rotation")
            except Exception as e:
                print(f"[Scheduler] Error initializing provider '{provider_name}': {e}")

    def _get_provider_list(self):
        """
        Get list of providers to initialize.

        Default implementation returns simple rotation list.
        Subclasses can override to provide different provider lists.

        Returns:
            List of provider entries (dicts with 'name' key)
        """
        return self.scheduler_config.get("provider_rotation", [])

    def _get_display_duration(self, provider_name: str, data: Any, override_duration: int = None) -> int:
        """
        Get display duration for a provider.

        Priority:
        1. Explicit override duration passed to this method
        2. Provider's suggested_display_duration from metadata
        3. Scheduler's default_display_duration

        Args:
            provider_name: Name of the provider
            data: DisplayData from provider
            override_duration: Optional explicit duration override

        Returns:
            Duration in seconds
        """
        # Check explicit override
        if override_duration is not None:
            return override_duration

        # Check provider's suggested duration
        if hasattr(data, "metadata") and data.metadata:
            suggested = data.metadata.get("suggested_display_duration")
            if suggested is not None:
                return suggested

        # Fall back to default
        return self.default_duration

    def _display_provider(self, provider_name: str, duration_override: int = None) -> bool:
        """
        Fetch data from provider, render it, and display/post.

        Args:
            provider_name: Name of provider to display
            duration_override: Optional duration override (in seconds)

        Returns:
            True if successful, False if error occurred
        """
        # Skip if provider not initialized
        if provider_name not in self.providers:
            print(f"[{self._timestamp()}] Skipping '{provider_name}' (not initialized)")
            return False

        provider = self.providers[provider_name]

        try:
            # Fetch data from provider (respects cache)
            data = provider.get_data()

            if self.debug:
                # Debug mode: render ASCII and print to console
                ascii_output = self.ascii_renderer.render(data)
                print()
                print("─" * 70)
                print(ascii_output)
                print("─" * 70)
                print()
            else:
                # Normal mode: render bitmap and post to matrix
                bitmap = self.renderer.render(data)
                success = self.client.post_bitmap(bitmap)

                if success:
                    print(f"[{self._timestamp()}] ✓ Successfully posted bitmap for '{provider_name}'")
                else:
                    print(f"[{self._timestamp()}] ✗ Failed to post bitmap for '{provider_name}'")

            # Get display duration and sleep
            duration = self._get_display_duration(provider_name, data, duration_override)
            print(f"[{self._timestamp()}] Displaying for {duration}s...")
            print()

            # Sleep in 1-second intervals to allow quick shutdown
            import time
            for _ in range(duration):
                if self.shutdown_requested:
                    break
                time.sleep(1)

            return True

        except Exception as e:
            print(f"[{self._timestamp()}] Error with provider '{provider_name}': {e}")
            print(f"[{self._timestamp()}] Skipping to next provider...")
            print()
            # Brief pause before continuing
            import time
            time.sleep(2)
            return False

    def shutdown(self):
        """Request graceful shutdown."""
        print()
        print("=" * 70)
        print(f"[{self._timestamp()}] Shutdown requested...")
        print("=" * 70)
        self.shutdown_requested = True

    def _timestamp(self) -> str:
        """Get current timestamp for logging."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @abstractmethod
    def run(self):
        """
        Main scheduler loop.

        Subclasses must implement their specific scheduling logic.
        """
        pass
