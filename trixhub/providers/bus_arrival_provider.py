"""
Bus arrival data provider using GTFS and GTFS-Realtime.

Fetches bus arrivals from GTFS static schedule and GTFS-Realtime feeds,
merging them to show both scheduled (SC) and realtime (TT) predictions.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from .base import DataProvider, DisplayData
from ..config import get_config
from ..gtfs import GTFSManager


class BusArrivalProvider(DataProvider):
    """
    Provider for bus arrival predictions.

    Uses GTFS static data and GTFS-Realtime feeds to show upcoming bus arrivals
    with both scheduled (SC) and real-time (TT) information.

    Features:
    - Priority route sorting (configured routes appear first)
    - Color-coded urgency (red <5min, yellow 5-10min, green 10+ min)
    - Automatic fallback to scheduled data if realtime unavailable
    """

    def __init__(self, stop_id: str = None, priority_routes: List[str] = None,
                 gtfs_static_url: str = None, gtfs_realtime_url: str = None,
                 config_key: str = None):
        """
        Initialize bus arrival provider.

        Args:
            stop_id: Transit stop ID to monitor (required)
            priority_routes: List of route numbers to show first (e.g., ["67", "69"])
            gtfs_static_url: URL to GTFS static ZIP (if None, uses config)
            gtfs_realtime_url: URL to GTFS-Realtime feed (if None, uses config)
            config_key: Config key to use (if None, uses "bus")
        """
        super().__init__()

        # Get config if parameters not provided
        # Use the config_key to look up the right section (e.g., "bus_7637")
        config_key = config_key or "bus"
        config = get_config().get_provider_config(config_key)

        self.stop_id = stop_id or config.get("stop_id")
        if not self.stop_id:
            raise ValueError("stop_id is required for BusArrivalProvider")

        self.priority_routes = priority_routes or config.get("priority_routes", [])

        # Get GTFS URLs
        self.gtfs_static_url = gtfs_static_url or config.get(
            "gtfs_static_url",
            "https://www.rideprt.org/GTFS/google_transit.zip"
        )
        self.gtfs_realtime_url = gtfs_realtime_url or config.get(
            "gtfs_realtime_url",
            "https://realtime.portauthority.org/bustime/gtfs-rt/tripupdates"
        )

        # Initialize GTFS manager
        self.gtfs_manager = GTFSManager(
            static_url=self.gtfs_static_url,
            realtime_url=self.gtfs_realtime_url
        )

        # Config
        self.max_arrivals = config.get("max_arrivals", 4)
        self.window_minutes = config.get("window_minutes", 60)

    def fetch_data(self) -> DisplayData:
        """
        Fetch bus arrival data from GTFS feeds.

        Returns:
            DisplayData with upcoming bus arrivals
        """
        try:
            # Get merged arrivals from GTFS manager
            arrivals = self.gtfs_manager.get_merged_arrivals(
                stop_id=self.stop_id,
                window_minutes=self.window_minutes
            )

            # Apply priority sorting
            arrivals = self._sort_by_priority(arrivals)

            # Limit to max arrivals
            arrivals = arrivals[:self.max_arrivals]

            # Add urgency level for color coding
            for arrival in arrivals:
                arrival['urgency'] = self._calculate_urgency(arrival['minutes_until'])

            # Build DisplayData
            return DisplayData(
                timestamp=datetime.now(),
                content={
                    "type": "bus_arrivals",
                    "stop_id": self.stop_id,
                    "arrivals": arrivals,
                    "has_realtime": any(a['type'] == 'TT' for a in arrivals)
                },
                metadata={
                    "priority": "normal",
                    "suggested_display_duration": 30,
                }
            )

        except Exception as e:
            # Return error data
            print(f"[BusArrivalProvider] Error fetching arrivals: {e}")
            return DisplayData(
                timestamp=datetime.now(),
                content={
                    "type": "bus_arrivals",
                    "stop_id": self.stop_id,
                    "error": True,
                    "error_message": "Bus data unavailable",
                    "error_details": str(e),
                    "arrivals": []
                },
                metadata={
                    "priority": "normal",
                    "suggested_display_duration": 30,
                }
            )

    def _sort_by_priority(self, arrivals: List[dict]) -> List[dict]:
        """
        Sort arrivals with priority routes first, then by time.

        Args:
            arrivals: List of arrival dicts

        Returns:
            Sorted list
        """
        def sort_key(arrival):
            route = arrival['route_short_name']
            minutes = arrival['minutes_until']

            # Priority routes get negative index (appear first)
            if route in self.priority_routes:
                priority = self.priority_routes.index(route)
                return (0, priority, minutes)  # Sort priority routes by priority, then time
            else:
                return (1, 999, minutes)  # Non-priority sorted only by time

        return sorted(arrivals, key=sort_key)

    def _calculate_urgency(self, minutes: int) -> str:
        """
        Calculate urgency level for color coding.

        Args:
            minutes: Minutes until arrival

        Returns:
            'urgent' (red), 'soon' (yellow), or 'normal' (green)
        """
        if minutes < 5:
            return 'urgent'  # Red
        elif minutes < 10:
            return 'soon'    # Yellow
        else:
            return 'normal'  # Green

    def get_cache_duration(self) -> timedelta:
        """
        Cache bus data for 30 seconds.

        Balances API load with freshness for real-time arrivals.

        Returns:
            30 second cache duration
        """
        return timedelta(seconds=30)
