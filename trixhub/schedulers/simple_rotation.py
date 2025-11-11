"""
Simple rotation scheduler for trix-hub.

Cycles through configured providers in sequence.
"""

from .base import BaseScheduler


class SimpleRotationScheduler(BaseScheduler):
    """
    Simple rotation scheduler.

    Cycles through configured providers in sequence, rendering bitmaps
    and posting them to the Matrix Portal display.
    """

    def __init__(self, debug: bool = False, quiet: bool = False):
        """
        Initialize simple rotation scheduler.

        Args:
            debug: If True, use ASCII renderer and print to console
            quiet: If True, reduce logging output to minimize SD card wear
        """
        super().__init__(debug=debug, quiet=quiet)

        # Get provider rotation order
        self.provider_rotation = self.scheduler_config.get("provider_rotation", [])

    def _get_provider_list(self):
        """Get list of providers to initialize from rotation config."""
        return self.scheduler_config.get("provider_rotation", [])

    def _get_provider_duration_override(self, provider_name: str) -> int:
        """
        Get duration override from rotation config for a provider.

        Args:
            provider_name: Name of provider

        Returns:
            Duration in seconds, or None if no override
        """
        for entry in self.provider_rotation:
            if entry.get("name") == provider_name and "duration" in entry:
                return entry["duration"]
        return None

    def run(self):
        """
        Main scheduler loop.

        Cycles through providers, rendering and posting bitmaps.
        """
        print("=" * 70)
        print("trix-hub Simple Rotation Scheduler")
        if self.debug:
            print("*** DEBUG MODE - ASCII Output ***")
        if self.quiet:
            print("*** QUIET MODE - Minimal Logging ***")
        print("=" * 70)
        print(f"Mode: {self.scheduler_config.get('mode', 'simple_rotation')}")
        print(f"Default display duration: {self.default_duration}s")
        print(f"Providers in rotation: {', '.join([p.get('name') for p in self.provider_rotation])}")
        if not self.debug:
            print(f"Matrix server: {self.matrix_config.get('server_hostname')}")
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

                # Get duration override from rotation config
                duration_override = self._get_provider_duration_override(provider_name)

                # Display provider
                if not self.quiet:
                    print(f"[{self._timestamp()}] Rotation #{rotation_count} - Provider: {provider_name}")
                self._display_provider(provider_name, duration_override)
