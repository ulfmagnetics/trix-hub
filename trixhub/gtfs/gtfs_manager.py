"""
GTFS and GTFS-Realtime data manager.

Handles downloading, parsing, and querying GTFS static schedule data,
plus fetching and merging GTFS-Realtime trip updates.
"""

import os
import zipfile
import tempfile
import shutil
from datetime import datetime, timedelta, time as dt_time
from typing import List, Dict, Any, Optional
import requests
from google.transit import gtfs_realtime_pb2
import gtfs_kit as gk


class GTFSManager:
    """
    Manages GTFS static and realtime data for a transit agency.

    Handles:
    - Downloading and caching GTFS static feeds
    - Parsing static schedule data
    - Fetching GTFS-Realtime trip updates
    - Merging scheduled and realtime arrivals
    """

    def __init__(self, static_url: str, realtime_url: str, cache_dir: str = None):
        """
        Initialize GTFS manager.

        Args:
            static_url: URL to GTFS static ZIP file
            realtime_url: URL to GTFS-Realtime trip updates feed
            cache_dir: Directory to cache GTFS data (default: temp directory)
        """
        self.static_url = static_url
        self.realtime_url = realtime_url

        # Set up cache directory
        if cache_dir is None:
            self.cache_dir = os.path.join(tempfile.gettempdir(), "trix-hub-gtfs")
        else:
            self.cache_dir = cache_dir

        os.makedirs(self.cache_dir, exist_ok=True)

        # GTFS feed object (loaded lazily)
        self.feed = None
        self.last_static_update = None

    def _download_static_feed(self) -> str:
        """
        Download GTFS static ZIP file.

        Returns:
            Path to downloaded ZIP file
        """
        zip_path = os.path.join(self.cache_dir, "gtfs_static.zip")

        print(f"[GTFSManager] Downloading GTFS static data from {self.static_url}")
        response = requests.get(self.static_url, timeout=30)
        response.raise_for_status()

        with open(zip_path, 'wb') as f:
            f.write(response.content)

        print(f"[GTFSManager] Downloaded GTFS static data ({len(response.content)} bytes)")
        return zip_path

    def _load_static_feed(self, force_refresh: bool = False) -> gk.Feed:
        """
        Load GTFS static feed into memory.

        Args:
            force_refresh: If True, download fresh data even if cached

        Returns:
            GTFSKit Feed object
        """
        # Check if we need to refresh
        should_refresh = force_refresh
        if self.last_static_update is None:
            should_refresh = True
        elif datetime.now() - self.last_static_update > timedelta(days=1):
            should_refresh = True

        # Use cached feed if available and fresh
        if not should_refresh and self.feed is not None:
            return self.feed

        # Download and extract GTFS data
        zip_path = self._download_static_feed()
        extract_dir = os.path.join(self.cache_dir, "gtfs_extracted")

        # Clean and recreate extraction directory
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Load with GTFSKit
        print("[GTFSManager] Loading GTFS data with GTFSKit...")
        self.feed = gk.read_feed(extract_dir, dist_units='km')
        self.last_static_update = datetime.now()

        print(f"[GTFSManager] Loaded GTFS feed with {len(self.feed.routes)} routes")
        return self.feed

    def get_scheduled_arrivals(self, stop_id: str, window_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get scheduled arrivals for a stop from GTFS static data.

        Args:
            stop_id: Stop ID to query
            window_minutes: Look ahead this many minutes (default: 60)

        Returns:
            List of arrival dicts with keys: route_id, route_short_name, trip_id,
            direction_id, headsign, arrival_time (datetime), type="SC"
        """
        # Ensure feed is loaded
        feed = self._load_static_feed()

        # Get current time
        now = datetime.now()
        current_time_seconds = now.hour * 3600 + now.minute * 60 + now.second
        window_end_seconds = current_time_seconds + (window_minutes * 60)

        # Get current service date
        # For simplicity, we'll use today's date and day of week
        # A more robust implementation would handle service_id properly
        weekday = now.strftime('%A').lower()  # 'monday', 'tuesday', etc.

        arrivals = []

        try:
            # Get stop times for this stop
            stop_times = feed.stop_times[feed.stop_times['stop_id'] == stop_id].copy()

            if stop_times.empty:
                print(f"[GTFSManager] Warning: No stop times found for stop {stop_id}")
                return []

            # Convert arrival_time to seconds since midnight
            # GTFS times can be > 24:00:00 for trips past midnight
            def parse_gtfs_time(time_str):
                """Parse GTFS time string (HH:MM:SS) to seconds since midnight."""
                if not isinstance(time_str, str):
                    return None
                parts = time_str.split(':')
                if len(parts) != 3:
                    return None
                try:
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
                except ValueError:
                    return None

            stop_times['arrival_seconds'] = stop_times['arrival_time'].apply(parse_gtfs_time)
            stop_times = stop_times.dropna(subset=['arrival_seconds'])

            # Filter to upcoming arrivals within window
            # Note: This is simplified - doesn't handle trips past midnight well
            upcoming = stop_times[
                (stop_times['arrival_seconds'] >= current_time_seconds) &
                (stop_times['arrival_seconds'] <= window_end_seconds)
            ]

            # Join with trips to get route and headsign
            trips_df = feed.trips
            upcoming = upcoming.merge(trips_df[['trip_id', 'route_id', 'direction_id', 'trip_headsign']],
                                     on='trip_id', how='left')

            # Join with routes to get route short name
            routes_df = feed.routes
            upcoming = upcoming.merge(routes_df[['route_id', 'route_short_name']],
                                     on='route_id', how='left')

            # Convert to arrival dicts
            for _, row in upcoming.iterrows():
                # Calculate arrival datetime
                arrival_seconds = int(row['arrival_seconds'])
                arrival_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
                arrival_dt += timedelta(seconds=arrival_seconds)

                # Extract direction (IB/OB)
                direction = self._format_direction(row.get('direction_id'))

                arrivals.append({
                    'route_id': row['route_id'],
                    'route_short_name': str(row.get('route_short_name', row['route_id'])),
                    'trip_id': row['trip_id'],
                    'direction': direction,
                    'headsign': row.get('trip_headsign', ''),
                    'arrival_time': arrival_dt,
                    'type': 'SC'  # Scheduled
                })

        except Exception as e:
            print(f"[GTFSManager] Error getting scheduled arrivals: {e}")
            return []

        return arrivals

    def get_realtime_arrivals(self, stop_id: str) -> List[Dict[str, Any]]:
        """
        Get realtime arrivals from GTFS-Realtime feed.

        Args:
            stop_id: Stop ID to query

        Returns:
            List of arrival dicts with keys: route_id, trip_id, arrival_time (datetime), type="TT"
        """
        arrivals = []

        try:
            # Fetch GTFS-Realtime feed
            response = requests.get(self.realtime_url, timeout=10)
            response.raise_for_status()

            # Parse protobuf
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)

            # Extract trip updates for this stop
            for entity in feed.entity:
                if not entity.HasField('trip_update'):
                    continue

                trip_update = entity.trip_update
                trip_id = trip_update.trip.trip_id
                route_id = trip_update.trip.route_id if trip_update.trip.HasField('route_id') else None

                # Check stop time updates
                for stop_time_update in trip_update.stop_time_update:
                    if stop_time_update.stop_id != stop_id:
                        continue

                    # Get arrival time
                    if stop_time_update.HasField('arrival'):
                        arrival_timestamp = stop_time_update.arrival.time
                        arrival_dt = datetime.fromtimestamp(arrival_timestamp)

                        arrivals.append({
                            'trip_id': trip_id,
                            'route_id': route_id,
                            'arrival_time': arrival_dt,
                            'type': 'TT'  # TrueTime (realtime)
                        })

        except requests.RequestException as e:
            print(f"[GTFSManager] Error fetching GTFS-Realtime: {e}")
            return []
        except Exception as e:
            print(f"[GTFSManager] Error parsing GTFS-Realtime: {e}")
            return []

        return arrivals

    def get_merged_arrivals(self, stop_id: str, window_minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get merged scheduled and realtime arrivals.

        Realtime data (TT) takes precedence over scheduled (SC) for the same trip.

        Args:
            stop_id: Stop ID to query
            window_minutes: Look ahead window in minutes

        Returns:
            Sorted list of arrivals with all fields populated
        """
        # Get both scheduled and realtime
        scheduled = self.get_scheduled_arrivals(stop_id, window_minutes)
        realtime = self.get_realtime_arrivals(stop_id)

        # Create map of trip_id -> realtime arrival for quick lookup
        realtime_map = {a['trip_id']: a for a in realtime}

        # Merge: use realtime if available, otherwise scheduled
        merged = []
        scheduled_trip_ids = set()

        # Process scheduled arrivals
        for arrival in scheduled:
            trip_id = arrival['trip_id']
            scheduled_trip_ids.add(trip_id)

            if trip_id in realtime_map:
                # Use realtime data for this trip
                rt = realtime_map[trip_id]
                merged.append({
                    'route_short_name': arrival['route_short_name'],
                    'route_id': arrival['route_id'],
                    'direction': arrival['direction'],
                    'headsign': arrival['headsign'],
                    'arrival_time': rt['arrival_time'],
                    'type': 'TT',
                    'trip_id': trip_id
                })
            else:
                # Use scheduled data
                merged.append(arrival)

        # Add any realtime arrivals that weren't in scheduled data
        for rt in realtime:
            if rt['trip_id'] not in scheduled_trip_ids:
                # Need to look up route info from feed
                try:
                    trip_info = self._get_trip_info(rt['trip_id'])
                    merged.append({
                        'route_short_name': trip_info.get('route_short_name', rt.get('route_id', '?')),
                        'route_id': rt.get('route_id', '?'),
                        'direction': trip_info.get('direction', ''),
                        'headsign': trip_info.get('headsign', ''),
                        'arrival_time': rt['arrival_time'],
                        'type': 'TT',
                        'trip_id': rt['trip_id']
                    })
                except Exception:
                    # Skip if we can't get trip info
                    pass

        # Filter to window and future arrivals only
        now = datetime.now()
        cutoff = now + timedelta(minutes=window_minutes)
        merged = [a for a in merged if now <= a['arrival_time'] <= cutoff]

        # Sort by arrival time
        merged.sort(key=lambda x: x['arrival_time'])

        # Calculate minutes until arrival
        for arrival in merged:
            minutes = int((arrival['arrival_time'] - now).total_seconds() / 60)
            arrival['minutes_until'] = max(0, minutes)  # Don't show negative

        return merged

    def _get_trip_info(self, trip_id: str) -> Dict[str, str]:
        """
        Look up trip information from GTFS static feed.

        Args:
            trip_id: Trip ID to look up

        Returns:
            Dict with route_short_name, direction, headsign
        """
        feed = self._load_static_feed()

        # Find trip
        trip_row = feed.trips[feed.trips['trip_id'] == trip_id]
        if trip_row.empty:
            return {}

        trip = trip_row.iloc[0]
        route_id = trip['route_id']

        # Find route
        route_row = feed.routes[feed.routes['route_id'] == route_id]
        route_short_name = route_row.iloc[0]['route_short_name'] if not route_row.empty else route_id

        return {
            'route_short_name': str(route_short_name),
            'direction': self._format_direction(trip.get('direction_id')),
            'headsign': trip.get('trip_headsign', '')
        }

    def _format_direction(self, direction_id) -> str:
        """
        Format direction ID as IB/OB.

        Args:
            direction_id: 0 or 1 from GTFS (or None)

        Returns:
            'IB' or 'OB' or ''
        """
        if direction_id is None or direction_id == '':
            return ''

        try:
            # GTFS standard: 0 = outbound, 1 = inbound (but agencies vary)
            # For PRT, we'll use: 0 = OB, 1 = IB
            direction_int = int(direction_id)
            return 'IB' if direction_int == 1 else 'OB'
        except (ValueError, TypeError):
            return ''
