"""
Condition evaluation for provider scheduling.

Supports date-based conditions for conditional provider triggering.
Examples: birthdays, holidays, weekends, seasonal content.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional


class ConditionEvaluator:
    """
    Evaluates whether conditions are met for provider execution.

    Supports multiple condition types that can be combined (AND logic).
    All conditions must pass for the provider to run.
    """

    def __init__(self, conditions: Dict[str, Any]):
        """
        Initialize condition evaluator.

        Args:
            conditions: Dictionary of condition configs from provider config
        """
        self.conditions = conditions or {}

    def should_run(self) -> bool:
        """
        Evaluate all conditions (AND logic).

        Returns:
            True if all conditions pass (or no conditions), False otherwise
        """
        if not self.conditions:
            return True

        # All conditions must pass (AND logic)
        # None means condition not configured, skip it
        checks = [
            self._check_date_match(),
            self._check_date_range(),
            self._check_day_of_week(),
            self._check_months()
        ]

        return all(check for check in checks if check is not None)

    def _check_date_match(self) -> Optional[bool]:
        """
        Check if today matches any date in date_match list.

        Config format: "date_match": ["MM-DD", "MM-DD", ...]
        Example: ["01-15", "06-22", "12-25"] for specific dates

        Returns:
            True if today matches, False if not, None if not configured
        """
        date_list = self.conditions.get("date_match")
        if not date_list:
            return None

        now = datetime.now()
        today = now.strftime("%m-%d")
        return today in date_list

    def _check_date_range(self) -> Optional[bool]:
        """
        Check if today is within date_range.

        Config format: "date_range": ["MM-DD", "MM-DD"]
        Supports year wraparound (e.g., ["12-20", "01-10"] for winter holidays)

        Returns:
            True if in range, False if not, None if not configured
        """
        date_range = self.conditions.get("date_range")
        if not date_range or len(date_range) != 2:
            return None

        now = datetime.now()
        today = now.strftime("%m-%d")
        start, end = date_range

        # Handle year wraparound (e.g., 12-20 to 01-10)
        if start <= end:
            # Normal range (e.g., 06-01 to 08-31 for summer)
            return start <= today <= end
        else:
            # Wraparound range (e.g., 12-20 to 01-10 for winter holidays)
            return today >= start or today <= end

    def _check_day_of_week(self) -> Optional[bool]:
        """
        Check if today is in day_of_week list.

        Config format: "day_of_week": [0, 1, 2, ...]
        Where 0=Sunday, 1=Monday, ..., 6=Saturday

        Returns:
            True if matches, False if not, None if not configured
        """
        days = self.conditions.get("day_of_week")
        if not days:
            return None

        now = datetime.now()
        # Python datetime: 0=Monday, 6=Sunday
        # Our config: 0=Sunday, 6=Saturday
        # Convert: (Python weekday + 1) % 7
        weekday = (now.weekday() + 1) % 7
        return weekday in days

    def _check_months(self) -> Optional[bool]:
        """
        Check if current month is in months list.

        Config format: "months": [1, 2, 3, ...]
        Where 1=January, 12=December

        Returns:
            True if matches, False if not, None if not configured
        """
        months = self.conditions.get("months")
        if not months:
            return None

        now = datetime.now()
        return now.month in months
