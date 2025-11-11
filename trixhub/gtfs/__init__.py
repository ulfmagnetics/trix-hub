"""
GTFS data handling for transit information.

Manages static GTFS schedule data and GTFS-Realtime feeds.
"""

from .gtfs_manager import GTFSManager, get_gtfs_manager

__all__ = ["GTFSManager", "get_gtfs_manager"]
