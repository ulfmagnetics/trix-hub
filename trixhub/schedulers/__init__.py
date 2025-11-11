"""
Schedulers for trix-hub.

Provides different scheduling modes for provider rotation.
"""

from .base import BaseScheduler
from .simple_rotation import SimpleRotationScheduler
from .time_windowed import TimeWindowedScheduler


def get_scheduler(config, debug: bool = False, quiet: bool = False):
    """
    Factory function to create appropriate scheduler based on config.

    Args:
        config: Config instance
        debug: If True, use ASCII renderer and print to console
        quiet: If True, reduce logging output to minimize SD card wear

    Returns:
        Scheduler instance (BaseScheduler subclass)
    """
    scheduler_config = config.get_scheduler_config()
    mode = scheduler_config.get("mode", "simple_rotation")

    if mode == "simple_rotation":
        return SimpleRotationScheduler(debug=debug, quiet=quiet)
    elif mode == "time_windowed_rotation":
        return TimeWindowedScheduler(debug=debug, quiet=quiet)
    else:
        raise ValueError(f"Unknown scheduler mode: {mode}. "
                        f"Valid modes: simple_rotation, time_windowed_rotation")


__all__ = [
    "BaseScheduler",
    "SimpleRotationScheduler",
    "TimeWindowedScheduler",
    "get_scheduler",
]
