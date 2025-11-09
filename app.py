#!/usr/bin/env python3
"""
trix-hub Application

LED Matrix Data Aggregation Hub for Raspberry Pi 5.
Rotates through configured data providers, rendering bitmaps and posting to trix-server.
"""

import argparse
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Any

from trixhub.config import get_config
from trixhub.providers import TimeProvider, WeatherProvider, DataProvider
from trixhub.renderers import BitmapRenderer, ASCIIRenderer
from trixhub.client import MatrixClient


class SimpleRotationScheduler:
    """
    Simple rotation scheduler for trix-hub.

    Cycles through configured providers in sequence, rendering bitmaps
    and posting them to the Matrix Portal display.
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
                server_url=self.matrix_config.get("server_url", "http://trix-server.local/display"),
                width=self.matrix_config.get("width", 64),
                height=self.matrix_config.get("height", 32),
                output_dir=self.matrix_config.get("output_dir", "output")
            )
            self.renderer = BitmapRenderer(
                width=self.matrix_config.get("width", 64),
                height=self.matrix_config.get("height", 32)
            )
            self.ascii_renderer = None

        # Initialize providers based on rotation config
        self.providers: Dict[str, DataProvider] = {}
        self._init_providers()

        # Get provider rotation order
        self.provider_rotation = self.scheduler_config.get("provider_rotation", [])
        self.default_duration = self.scheduler_config.get("default_display_duration", 30)

    def _init_providers(self):
        """Initialize all configured providers."""
        # Map of provider names to classes
        provider_classes = {
            "time": TimeProvider,
            "weather": WeatherProvider,
        }

        # Get provider rotation to know which ones to initialize
        rotation = self.scheduler_config.get("provider_rotation", [])

        for provider_entry in rotation:
            provider_name = provider_entry.get("name")

            # Check if provider is enabled in config
            provider_config = self.config.get_provider_config(provider_name)
            if not provider_config.get("enabled", True):
                print(f"[Scheduler] Warning: Provider '{provider_name}' is in rotation but disabled in config")
                continue

            # Initialize provider if we have a class for it
            if provider_name in provider_classes:
                try:
                    self.providers[provider_name] = provider_classes[provider_name]()
                    print(f"[Scheduler] Initialized provider: {provider_name}")
                except Exception as e:
                    print(f"[Scheduler] Error initializing provider '{provider_name}': {e}")
            else:
                print(f"[Scheduler] Warning: Unknown provider '{provider_name}' in rotation")

    def _get_display_duration(self, provider_name: str, data: Any) -> int:
        """
        Get display duration for a provider.

        Priority:
        1. Provider-specific override in rotation config
        2. Provider's suggested_display_duration from metadata
        3. Scheduler's default_display_duration

        Args:
            provider_name: Name of the provider
            data: DisplayData from provider

        Returns:
            Duration in seconds
        """
        # Check rotation config for override
        for entry in self.provider_rotation:
            if entry.get("name") == provider_name and "duration" in entry:
                return entry["duration"]

        # Check provider's suggested duration
        if hasattr(data, "metadata") and data.metadata:
            suggested = data.metadata.get("suggested_display_duration")
            if suggested is not None:
                return suggested

        # Fall back to default
        return self.default_duration

    def run(self):
        """
        Main scheduler loop.

        Cycles through providers, rendering and posting bitmaps.
        """
        print("=" * 70)
        print("trix-hub Simple Rotation Scheduler")
        if self.debug:
            print("*** DEBUG MODE - ASCII Output ***")
        print("=" * 70)
        print(f"Mode: {self.scheduler_config.get('mode', 'simple_rotation')}")
        print(f"Default display duration: {self.default_duration}s")
        print(f"Providers in rotation: {', '.join([p.get('name') for p in self.provider_rotation])}")
        if not self.debug:
            print(f"Matrix server: {self.matrix_config.get('server_url')}")
        print(f"Display size: {self.matrix_config.get('width')}x{self.matrix_config.get('height')}")
        print("=" * 70)
        print()
        print("Starting rotation... (Press Ctrl+C to stop)")
        print()

        # Main rotation loop
        rotation_count = 0

        while not self.shutdown_requested:
            rotation_count += 1

            for provider_entry in self.provider_rotation:
                if self.shutdown_requested:
                    break

                provider_name = provider_entry.get("name")

                # Skip if provider not initialized
                if provider_name not in self.providers:
                    print(f"[{self._timestamp()}] Skipping '{provider_name}' (not initialized)")
                    continue

                provider = self.providers[provider_name]

                try:
                    # Fetch data from provider (respects cache)
                    print(f"[{self._timestamp()}] Rotation #{rotation_count} - Provider: {provider_name}")
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
                    duration = self._get_display_duration(provider_name, data)
                    print(f"[{self._timestamp()}] Displaying for {duration}s...")
                    print()

                    # Sleep in 1-second intervals to allow quick shutdown
                    for _ in range(duration):
                        if self.shutdown_requested:
                            break
                        time.sleep(1)

                except Exception as e:
                    print(f"[{self._timestamp()}] Error with provider '{provider_name}': {e}")
                    print(f"[{self._timestamp()}] Skipping to next provider...")
                    print()
                    # Brief pause before continuing
                    time.sleep(2)

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


def signal_handler(*_args):
    """Handle shutdown signals."""
    # Access the global scheduler instance
    if 'scheduler' in globals():
        scheduler.shutdown()
    else:
        print("\nShutdown requested")
        sys.exit(0)


def main():
    """Main entry point."""
    global scheduler

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="trix-hub - LED Matrix Data Aggregation Hub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py              Run in normal mode (post bitmaps to matrix)
  python app.py --debug      Run in debug mode (print ASCII to console)
        """
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: render ASCII to console instead of posting bitmaps"
    )
    args = parser.parse_args()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop

    try:
        # Create and run scheduler
        scheduler = SimpleRotationScheduler(debug=args.debug)
        scheduler.run()

    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        print()
        print("=" * 70)
        print("trix-hub stopped")
        print("=" * 70)


if __name__ == "__main__":
    main()
