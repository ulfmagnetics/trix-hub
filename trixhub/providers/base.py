"""
Base classes for data providers.

Providers fetch and structure data from various sources (APIs, calculations, etc.)
and return renderer-agnostic DisplayData objects.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from trixhub.conditions import ConditionEvaluator


@dataclass
class DisplayData:
    """
    Structured data from a provider - renderer-agnostic.

    Attributes:
        timestamp: When the data was fetched
        content: Provider-specific structured data (dict)
        metadata: Optional hints for renderers (e.g., display duration, priority)
    """
    timestamp: datetime
    content: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure metadata is never None"""
        if self.metadata is None:
            self.metadata = {}


class DataProvider(ABC):
    """
    Base class for data providers.

    Providers fetch data from sources and return structured DisplayData objects.
    Includes built-in caching to avoid redundant fetches.
    """

    def __init__(self):
        """Initialize provider with empty cache"""
        self._cache: Optional[DisplayData] = None
        self._cache_expires: Optional[datetime] = None
        self._condition_evaluator: Optional['ConditionEvaluator'] = None

    @abstractmethod
    def fetch_data(self) -> DisplayData:
        """
        Fetch and structure data from the source.

        Returns:
            DisplayData object with structured content

        Raises:
            Exception: If data fetching fails
        """
        pass

    def get_cache_duration(self) -> timedelta:
        """
        How long to cache data before fetching again.

        Returns:
            timedelta for cache duration (default: 0 seconds, no caching)
        """
        return timedelta(seconds=0)

    def get_data(self, force_refresh: bool = False) -> DisplayData:
        """
        Get data, using cache if available and not expired.

        Args:
            force_refresh: If True, ignore cache and fetch fresh data

        Returns:
            DisplayData object (from cache or freshly fetched)
        """
        now = datetime.now()

        # Check if we can use cached data
        if not force_refresh and self._cache and self._cache_expires:
            if now < self._cache_expires:
                return self._cache

        # Fetch fresh data
        data = self.fetch_data()

        # Update cache if caching is enabled
        cache_duration = self.get_cache_duration()
        if cache_duration.total_seconds() > 0:
            self._cache = data
            self._cache_expires = now + cache_duration

        return data

    def clear_cache(self):
        """Clear the cache, forcing next get_data() to fetch fresh data"""
        self._cache = None
        self._cache_expires = None

    def should_run(self) -> bool:
        """
        Check if provider should run based on configured conditions.

        Default implementation checks self._condition_evaluator if set by subclass.
        Subclasses can override for custom condition logic.

        Returns:
            True if provider should run, False to skip
        """
        if self._condition_evaluator is None:
            return True  # No conditions = always run
        return self._condition_evaluator.should_run()

    def _load_conditions(self, config: Dict[str, Any]):
        """
        Helper to load conditions from provider config.

        Subclasses should call this in __init__ if they support conditional execution.

        Args:
            config: Provider configuration dict
        """
        conditions_config = config.get("conditions", {})
        if conditions_config:
            from trixhub.conditions import ConditionEvaluator
            self._condition_evaluator = ConditionEvaluator(conditions_config)
