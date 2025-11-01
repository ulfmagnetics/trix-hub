"""
Data providers for trix-hub.

Providers fetch and structure data from various sources.
"""

from trixhub.providers.base import DisplayData, DataProvider
from trixhub.providers.time_provider import TimeProvider

__all__ = [
    "DisplayData",
    "DataProvider",
    "TimeProvider",
]
