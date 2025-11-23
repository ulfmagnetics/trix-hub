"""
Time-windowed rotation scheduler for trix-hub.

Supports different provider rotations for different times of day.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseScheduler
from trixhub.conditions import ConditionEvaluator


class TimeWindowedScheduler(BaseScheduler):
    """
    Time-windowed rotation scheduler.

    Switches between different provider rotations based on time of day.
    Supports midnight wraparound for time windows like 21:00-06:00.
    """

    def __init__(self, debug: bool = False, quiet: bool = False):
        """
        Initialize time-windowed rotation scheduler.

        Args:
            debug: If True, use ASCII renderer and print to console
            quiet: If True, reduce logging output to minimize SD card wear
        """
        # Pre-load rotations config before calling super().__init__()
        # This is needed because super().__init__() calls _init_providers()
        # which calls _get_provider_list() which needs rotations
        from trixhub.config import get_config
        temp_config = get_config()
        temp_scheduler_config = temp_config.get_scheduler_config()

        self.rotations = temp_scheduler_config.get("rotations", [])
        self.fallback_rotation = temp_scheduler_config.get("fallback_rotation", {
            "providers": [{"name": "time", "duration": 30}]
        })

        # Call super().__init__() - this will use our rotations
        super().__init__(debug=debug, quiet=quiet)

        # Validate rotations
        if not self.rotations:
            print("[Scheduler] Warning: No rotations configured, using fallback rotation only")

    def _get_provider_list(self):
        """
        Get list of all unique providers across all rotations.

        Returns:
            List of provider entries (dicts with 'name' key)
        """
        providers = []
        seen_names = set()

        # Collect from all rotations
        for rotation in self.rotations:
            if "providers" in rotation:
                for provider in rotation["providers"]:
                    name = provider.get("name")
                    if name and name not in seen_names:
                        providers.append(provider)
                        seen_names.add(name)

        # Add fallback rotation providers
        if "providers" in self.fallback_rotation:
            for provider in self.fallback_rotation["providers"]:
                name = provider.get("name")
                if name and name not in seen_names:
                    providers.append(provider)
                    seen_names.add(name)

        return providers

    def _parse_time(self, time_str: str) -> int:
        """
        Convert 'HH:MM' time string to minutes since midnight.

        Args:
            time_str: Time in 'HH:MM' format

        Returns:
            Minutes since midnight (0-1439)
        """
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format: {time_str}")
            hours = int(parts[0])
            minutes = int(parts[1])
            if not (0 <= hours <= 23) or not (0 <= minutes <= 59):
                raise ValueError(f"Time out of range: {time_str}")
            return hours * 60 + minutes
        except Exception as e:
            print(f"[Scheduler] Error parsing time '{time_str}': {e}")
            return 0

    def _is_time_in_window(self, current_minutes: int, start: str, end: str) -> bool:
        """
        Check if current time is within time window.

        Handles midnight wraparound (e.g., 21:00-06:00).

        Args:
            current_minutes: Current time in minutes since midnight
            start: Start time string 'HH:MM'
            end: End time string 'HH:MM'

        Returns:
            True if current time is in window [start, end)
        """
        start_min = self._parse_time(start)
        end_min = self._parse_time(end)

        if start_min <= end_min:
            # Normal window (e.g., 06:00-08:00)
            return start_min <= current_minutes < end_min
        else:
            # Midnight wraparound (e.g., 21:00-06:00)
            return current_minutes >= start_min or current_minutes < end_min

    def _get_current_minutes(self) -> int:
        """
        Get current time in minutes since midnight.

        Returns:
            Minutes since midnight (0-1439)
        """
        now = datetime.now()
        return now.hour * 60 + now.minute

    def _check_rotation_conditions(self, rotation: Dict[str, Any]) -> bool:
        """
        Check if rotation's conditions are met.

        Args:
            rotation: Rotation dict (may contain 'conditions' key)

        Returns:
            True if conditions pass (or no conditions configured), False otherwise
        """
        conditions = rotation.get("conditions")
        if not conditions:
            return True  # No conditions = always runs

        evaluator = ConditionEvaluator(conditions)
        return evaluator.should_run()

    def _get_active_rotation(self) -> Dict[str, Any]:
        """
        Get the rotation for the current time window.

        Checks both time window AND conditions for each rotation.
        Continues to next rotation if conditions don't match.

        Returns:
            Rotation dict, or fallback rotation if no match
        """
        current_minutes = self._get_current_minutes()

        for rotation in self.rotations:
            time_window = rotation.get("time_window", {})
            start = time_window.get("start")
            end = time_window.get("end")

            if start and end:
                # Check if time window matches
                if self._is_time_in_window(current_minutes, start, end):
                    # Check if conditions match
                    if self._check_rotation_conditions(rotation):
                        # Both time and conditions match!
                        return rotation
                    else:
                        # Time matches but conditions don't - continue to next rotation
                        if not self.quiet:
                            rotation_name = rotation.get("name", "unnamed")
                            print(f"[{self._timestamp()}] Rotation '{rotation_name}' time matches but conditions not met, checking next...")

        # No matching rotation, return fallback
        return self.fallback_rotation

    def _should_switch_rotation(self, current_rotation_name: str) -> bool:
        """
        Check if we should switch to a different rotation.

        Args:
            current_rotation_name: Name of current rotation

        Returns:
            True if time window has changed
        """
        active_rotation = self._get_active_rotation()
        active_name = active_rotation.get("name", "fallback")
        return active_name != current_rotation_name

    def _handle_blank_screen(self, rotation: Dict[str, Any]):
        """
        Handle blank screen rotation.

        Clears display and sleeps until rotation should change.

        Args:
            rotation: Rotation dict with blank_screen: true
        """
        rotation_name = rotation.get("name", "blank")

        # Clear display if not in debug mode
        if not self.debug and self.client:
            if not self.quiet:
                print(f"[{self._timestamp()}] Clearing display for '{rotation_name}' rotation")
            self.client.clear_display()
        else:
            if not self.quiet:
                print(f"[{self._timestamp()}] Blank screen rotation: '{rotation_name}'")

        # Sleep in 5-second intervals, checking for rotation changes
        if not self.quiet:
            print(f"[{self._timestamp()}] Waiting for next rotation...")
            print()

        while not self.shutdown_requested:
            # Check if we should switch rotation
            if self._should_switch_rotation(rotation_name):
                print(f"[{self._timestamp()}] Time window changed, switching rotation")
                break

            # Sleep for 5 seconds
            for _ in range(5):
                if self.shutdown_requested:
                    break
                time.sleep(1)

    def _run_rotation(self, rotation: Dict[str, Any]):
        """
        Run one cycle of a rotation.

        Args:
            rotation: Rotation dict with providers list
        """
        rotation_name = rotation.get("name", "fallback")
        providers = rotation.get("providers", [])

        if not providers:
            print(f"[{self._timestamp()}] Warning: Rotation '{rotation_name}' has no providers")
            return

        for provider_entry in providers:
            if self.shutdown_requested:
                break

            # Check if we should switch rotation (time window changed)
            if self._should_switch_rotation(rotation_name):
                print(f"[{self._timestamp()}] Time window changed, switching rotation")
                break

            provider_name = provider_entry.get("name")
            duration_override = provider_entry.get("duration")

            # Display provider
            if not self.quiet:
                print(f"[{self._timestamp()}] Rotation: {rotation_name} - Provider: {provider_name}")
            self._display_provider(provider_name, duration_override)

    def run(self):
        """
        Main scheduler loop.

        Switches between rotations based on time windows.
        """
        print("=" * 70)
        print("trix-hub Time-Windowed Rotation Scheduler")
        if self.debug:
            print("*** DEBUG MODE - ASCII Output ***")
        if self.quiet:
            print("*** QUIET MODE - Minimal Logging ***")
        print("=" * 70)
        print(f"Mode: {self.scheduler_config.get('mode', 'time_windowed_rotation')}")
        print(f"Default display duration: {self.default_duration}s")
        print(f"Rotations configured: {len(self.rotations)}")
        if not self.debug:
            print(f"Matrix server: {self.matrix_config.get('server_hostname')}")
        print(f"Display size: {self.matrix_config.get('width')}x{self.matrix_config.get('height')}")
        print("=" * 70)
        print()
        print("Time Windows:")
        for rotation in self.rotations:
            name = rotation.get("name", "unnamed")
            window = rotation.get("time_window", {})
            start = window.get("start", "?")
            end = window.get("end", "?")
            is_blank = rotation.get("blank_screen", False)
            conditions = rotation.get("conditions")

            # Build condition description
            condition_desc = ""
            if conditions:
                parts = []
                if "date_match" in conditions:
                    parts.append(f"dates={','.join(conditions['date_match'])}")
                if "date_range" in conditions:
                    parts.append(f"range={'-'.join(conditions['date_range'])}")
                if "day_of_week" in conditions:
                    days = conditions['day_of_week']
                    day_names = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                    day_str = ','.join([day_names[d] for d in days if 0 <= d <= 6])
                    parts.append(f"days={day_str}")
                if "months" in conditions:
                    parts.append(f"months={','.join(map(str, conditions['months']))}")
                if parts:
                    condition_desc = f" [conditions: {'; '.join(parts)}]"

            if is_blank:
                print(f"  {name}: {start}-{end} (blank screen){condition_desc}")
            else:
                provider_names = [p.get("name") for p in rotation.get("providers", [])]
                print(f"  {name}: {start}-{end} -> {', '.join(provider_names)}{condition_desc}")
        print("=" * 70)
        print()
        print("Starting scheduler... (Press Ctrl+C to stop)")
        print()

        # Main scheduling loop
        cycle_count = 0

        while not self.shutdown_requested:
            cycle_count += 1

            # Get active rotation for current time
            active_rotation = self._get_active_rotation()
            rotation_name = active_rotation.get("name", "fallback")
            is_blank = active_rotation.get("blank_screen", False)

            if not self.quiet:
                print(f"[{self._timestamp()}] Cycle #{cycle_count} - Active rotation: {rotation_name}")

            if is_blank:
                # Handle blank screen rotation
                self._handle_blank_screen(active_rotation)
            else:
                # Run normal provider rotation
                self._run_rotation(active_rotation)
