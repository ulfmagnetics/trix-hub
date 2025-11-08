"""
Time display provider.

Provides current time and date information in various formats.
"""

from datetime import datetime, timedelta
from .base import DataProvider, DisplayData


class TimeProvider(DataProvider):
    """
    Provider for current time display.

    Fetches current system time and formats it for display.
    Caches for 30 seconds since second-by-second updates aren't necessary
    for typical LED matrix displays.
    """

    def fetch_data(self) -> DisplayData:
        """
        Fetch current time and format for display.

        Returns:
            DisplayData with time information in multiple formats
        """
        now = datetime.now()

        return DisplayData(
            timestamp=now,
            content={
                "type": "time",
                "time": now,
                "time_12h": now.strftime("%I:%M %p"),
                "time_24h": now.strftime("%H:%M"),
                "date": now.strftime("%Y-%m-%d"),
                "date_short": now.strftime("%m/%d"),
                "date_us": now.strftime("%m/%d/%Y"),
                "day_of_week": now.strftime("%A"),
                "day_of_week_short": now.strftime("%a"),
            },
            metadata={
                "priority": "normal",
                "suggested_display_duration": 30,  # seconds
            }
        )

    def get_cache_duration(self) -> timedelta:
        """
        Cache time data for 30 seconds.

        No need to fetch every second for typical display updates.

        Returns:
            30 second cache duration
        """
        return timedelta(seconds=30)
