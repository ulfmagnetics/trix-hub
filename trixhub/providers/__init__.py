"""
Data providers for trix-hub.

Providers fetch and structure data from various sources.
"""

from trixhub.providers.base import DisplayData, DataProvider
from trixhub.providers.time_provider import TimeProvider
from trixhub.providers.weather_provider import WeatherProvider
from trixhub.providers.bus_arrival_provider import BusArrivalProvider

__all__ = [
    "DisplayData",
    "DataProvider",
    "TimeProvider",
    "WeatherProvider",
    "BusArrivalProvider",
]
