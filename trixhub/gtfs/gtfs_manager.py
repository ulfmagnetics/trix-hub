"""
GTFS and GTFS-Realtime data manager.

Handles downloading, parsing, and querying GTFS static schedule data,
plus fetching and merging GTFS-Realtime trip updates.
"""

import os
import zipfile
import tempfile
import shutil
import pickle
import time
from datetime import datetime, timedelta, time as dt_time
from typing import List, Dict, Any, Optional
import requests
from google.transit import gtfs_realtime_pb2

# Lazy import gtfs_kit - only loaded when actually parsing GTFS data
# This defers ~26s import cost until first bus data fetch
_gtfs_kit = None

def _get_gtfs_kit():
    """Lazy load gtfs_kit only when needed."""
    global _gtfs_kit
    if _gtfs_kit is None:
        import gtfs_kit as gk
        _gtfs_kit = gk
    return _gtfs_kit

# Singleton registry for GTFSManager instances
# Key: (static_url, realtime_url) tuple
# Value: GTFSManager instance
_manager_instances = {}

def get_gtfs_manager(static_url: str, realtime_url: str,
                     cache_dir: str = None, cache_days: int = 30) -> 'GTFSManager':
    """
    Get or create a singleton GTFSManager instance.

    Multiple providers can share the same GTFSManager if they use the same
    GTFS feeds (static and realtime URLs).

    Args:
        static_url: URL to GTFS static ZIP file
        realtime_url: URL to GTFS-Realtime trip updates feed
        cache_dir: Directory to cache GTFS data (default: /app/cache/gtfs)
        cache_days: Days to cache pickled GTFS data (default: 30)

    Returns:
        Shared GTFSManager instance
    """
    key = (static_url, realtime_url)

    if key not in _manager_instances:
        print(f"[GTFSManager] Creating new singleton instance for {static_url}")
        _manager_instances[key] = GTFSManager(
            static_url=static_url,
            realtime_url=realtime_url,
            cache_dir=cache_dir,
            cache_days=cache_days
        )
    else:
        print(f"[GTFSManager] Reusing existing singleton instance for {static_url}")

    return _manager_instances[key]


class GTFSManager:
    """
    Manages GTFS static and realtime data for a transit agency.

    Handles:
    - Downloading and caching GTFS static feeds
    - Parsing static schedule data
    - Fetching GTFS-Realtime trip updates
    - Merging scheduled and realtime arrivals
    """

    def __init__(self, static_url: str, realtime_url: str, cache_dir: str = None, cache_days: int = 30):
        """
        Initialize GTFS manager.

        Args:
            static_url: URL to GTFS static ZIP file
            realtime_url: URL to GTFS-Realtime trip updates feed
            cache_dir: Directory to cache GTFS data (default: /app/cache/gtfs)
            cache_days: Days to cache pickled GTFS data (default: 30)
        """
        self.static_url = static_url
        self.realtime_url = realtime_url
        self.cache_days = cache_days

        # Set up cache directory - prefer persistent location
        if cache_dir is None:
            # Try to use persistent location, fall back to temp
            if os.path.exists("/app"):
                self.cache_dir = "/app/cache/gtfs"
            else:
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

    def _get_pickle_path(self) -> Optional[str]:
        """
        Find existing valid pickle file or return None.

        Returns:
            Path to valid pickle file, or None if no valid cache exists
        """
        # Look for pickle files matching pattern: gtfs_feed_*.pickle
        pickle_files = [f for f in os.listdir(self.cache_dir) if f.startswith("gtfs_feed_") and f.endswith(".pickle")]

        for pickle_file in pickle_files:
            # Extract expiration timestamp from filename
            try:
                # Format: gtfs_feed_{expiration_timestamp}.pickle
                expiration_str = pickle_file.replace("gtfs_feed_", "").replace(".pickle", "")
                expiration_timestamp = int(expiration_str)

                # Check if expired
                if time.time() < expiration_timestamp:
                    # Still valid
                    return os.path.join(self.cache_dir, pickle_file)
                else:
                    # Expired - delete it
                    expired_path = os.path.join(self.cache_dir, pickle_file)
                    print(f"[GTFSManager] Removing expired pickle: {pickle_file}")
                    os.remove(expired_path)
            except (ValueError, OSError) as e:
                # Invalid filename format or couldn't delete - skip
                print(f"[GTFSManager] Warning: Invalid pickle file {pickle_file}: {e}")
                continue

        return None

    def _save_pickle(self, feed) -> str:
        """
        Save GTFS feed to pickle file with expiration timestamp.

        Args:
            feed: GTFSKit feed object to pickle

        Returns:
            Path to saved pickle file
        """
        # Calculate expiration timestamp (now + cache_days)
        expiration_timestamp = int(time.time() + (self.cache_days * 86400))

        # Create filename with expiration timestamp
        pickle_filename = f"gtfs_feed_{expiration_timestamp}.pickle"
        pickle_path = os.path.join(self.cache_dir, pickle_filename)

        print(f"[GTFSManager] Saving pickled GTFS feed to {pickle_filename}")
        print(f"[GTFSManager] Cache expires: {datetime.fromtimestamp(expiration_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

        with open(pickle_path, 'wb') as f:
            pickle.dump(feed, f, protocol=pickle.HIGHEST_PROTOCOL)

        return pickle_path

    def _load_pickle(self, pickle_path: str):
        """
        Load GTFS feed from pickle file.

        Args:
            pickle_path: Path to pickle file

        Returns:
            GTFSKit feed object
        """
        print(f"[GTFSManager] Loading pickled GTFS feed from {os.path.basename(pickle_path)}")
        start_time = time.time()

        with open(pickle_path, 'rb') as f:
            feed = pickle.load(f)

        elapsed = time.time() - start_time
        print(f"[GTFSManager] Loaded pickled feed in {elapsed:.2f}s")

        return feed

    def _load_static_feed(self, force_refresh: bool = False):
        """
        Load GTFS static feed into memory.

        Uses pickle cache for fast loading (~1-2s vs ~60s parse time).
        Cache expiration is encoded in the pickle filename.

        Args:
            force_refresh: If True, download fresh data even if cached

        Returns:
            GTFSKit Feed object
        """
        # If we already have the feed in memory, return it
        if not force_refresh and self.feed is not None:
            return self.feed

        # Try to load from pickle cache (unless force refresh)
        if not force_refresh:
            pickle_path = self._get_pickle_path()
            if pickle_path:
                try:
                    self.feed = self._load_pickle(pickle_path)
                    self.last_static_update = datetime.now()
                    print(f"[GTFSManager] Loaded GTFS feed with {len(self.feed.routes)} routes")
                    return self.feed
                except Exception as e:
                    print(f"[GTFSManager] Error loading pickle, will download fresh: {e}")
                    # Fall through to download fresh data

        # No valid pickle cache - download and parse fresh data
        zip_path = self._download_static_feed()
        extract_dir = os.path.join(self.cache_dir, "gtfs_extracted")

        # Clean and recreate extraction directory
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir)

        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # Load with GTFSKit (lazy import here)
        print("[GTFSManager] Loading GTFS data with GTFSKit...")
        start_time = time.time()
        gk = _get_gtfs_kit()
        self.feed = gk.read_feed(extract_dir, dist_units='km')
        elapsed = time.time() - start_time
        self.last_static_update = datetime.now()

        print(f"[GTFSManager] Loaded GTFS feed with {len(self.feed.routes)} routes in {elapsed:.2f}s")

        # Save to pickle cache for next time
        try:
            self._save_pickle(self.feed)
        except Exception as e:
            print(f"[GTFSManager] Warning: Could not save pickle cache: {e}")

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
