"""
Weather data provider using Open-Meteo API.

Fetches current weather and short-term forecast for configured location.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import requests
import math

from .base import DataProvider, DisplayData
from ..config import get_config


class WeatherProvider(DataProvider):
    """
    Provider for weather data from Open-Meteo.

    Fetches current conditions and forecast for next N hours.
    No API key required.
    """

    # Weather code mapping (Open-Meteo WMO Weather interpretation codes)
    WEATHER_CONDITIONS = {
        0: "sunny",          # Clear sky
        1: "sunny",          # Mainly clear
        2: "partly_cloudy",  # Partly cloudy
        3: "cloudy",         # Overcast
        45: "cloudy",        # Fog
        48: "cloudy",        # Depositing rime fog
        51: "rainy",         # Drizzle: Light
        53: "rainy",         # Drizzle: Moderate
        55: "rainy",         # Drizzle: Dense
        61: "rainy",         # Rain: Slight
        63: "rainy",         # Rain: Moderate
        65: "rainy",         # Rain: Heavy
        71: "snowy",         # Snow fall: Slight
        73: "snowy",         # Snow fall: Moderate
        75: "snowy",         # Snow fall: Heavy
        77: "snowy",         # Snow grains
        80: "rainy",         # Rain showers: Slight
        81: "rainy",         # Rain showers: Moderate
        82: "rainy",         # Rain showers: Violent
        85: "snowy",         # Snow showers: Slight
        86: "snowy",         # Snow showers: Heavy
        95: "thunderstorm",  # Thunderstorm: Slight or moderate
        96: "thunderstorm",  # Thunderstorm with slight hail
        99: "thunderstorm",  # Thunderstorm with heavy hail
    }

    def __init__(self):
        """Initialize weather provider with configuration."""
        super().__init__()
        self.config = get_config().get_provider_config("weather")

        # Get location from config
        self.latitude = self.config.get("location", {}).get("latitude", 40.0)
        self.longitude = self.config.get("location", {}).get("longitude", -80.0)
        self.location_name = self.config.get("location", {}).get("name", "Unknown")

        # Get units and forecast settings
        self.units = self.config.get("units", "fahrenheit")
        self.forecast_interval_hours = self.config.get("forecast_interval_hours", 3)

    def fetch_data(self) -> DisplayData:
        """
        Fetch weather data from Open-Meteo API.

        Returns:
            DisplayData with current and forecast weather

        Raises:
            requests.RequestException: If API call fails
        """
        try:
            # Build weather API URL
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,weathercode,windspeed_10m,winddirection_10m",
                "hourly": "temperature_2m,weathercode",
                "daily": "sunrise,sunset",
                "temperature_unit": self.units,
                "windspeed_unit": "mph",
                "forecast_days": 1,
                "timezone": "auto"
            }

            # Fetch weather data
            response = requests.get(weather_url, params=weather_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse sunrise/sunset times
            sunrise_str = data["daily"]["sunrise"][0]
            sunset_str = data["daily"]["sunset"][0]
            sunrise = datetime.fromisoformat(sunrise_str.replace('Z', '+00:00'))
            sunset = datetime.fromisoformat(sunset_str.replace('Z', '+00:00'))

            # Check if it's currently nighttime
            now = datetime.now(sunrise.tzinfo)
            is_night = now < sunrise or now > sunset

            # Fetch AQI data if enabled
            aqi_value = None
            if self.config.get("aqi_enabled", True):
                try:
                    aqi_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
                    aqi_params = {
                        "latitude": self.latitude,
                        "longitude": self.longitude,
                        "current": "us_aqi",
                        "timezone": "auto"
                    }
                    aqi_response = requests.get(aqi_url, params=aqi_params, timeout=10)
                    aqi_response.raise_for_status()
                    aqi_data = aqi_response.json()
                    aqi_value = int(round(aqi_data["current"]["us_aqi"]))
                except (requests.RequestException, KeyError, ValueError, TypeError):
                    # AQI is optional, don't fail if it's unavailable
                    aqi_value = None

            # Calculate moon phase if it's nighttime
            moon_phase = None
            if is_night:
                moon_phase = self._calculate_moon_phase(now)

            # Parse current weather
            current_temp = int(round(data["current"]["temperature_2m"]))
            current_code = data["current"]["weathercode"]
            current_condition = self._map_weather_code(current_code, is_night, moon_phase)
            current_windspeed = int(round(data["current"]["windspeed_10m"]))
            current_wind_direction = int(round(data["current"]["winddirection_10m"]))

            # Parse hourly forecast data
            hourly_temps = data["hourly"]["temperature_2m"]
            hourly_codes = data["hourly"]["weathercode"]

            # Calculate time labels
            now = datetime.now()
            current_time_label = "Now"
            forecast1_time = now + timedelta(hours=self.forecast_interval_hours)
            forecast1_time_label = self._format_time_compact(forecast1_time)  # e.g., "3p"
            forecast2_time = now + timedelta(hours=self.forecast_interval_hours * 2)
            forecast2_time_label = self._format_time_compact(forecast2_time)  # e.g., "6p"

            # Get forecast for interval hours ahead (forecast 1)
            forecast1_index = min(self.forecast_interval_hours, len(hourly_temps) - 1)
            forecast1_temp = int(round(hourly_temps[forecast1_index]))
            forecast1_code = hourly_codes[forecast1_index]
            forecast1_condition = self._map_weather_code(forecast1_code, is_night, moon_phase)

            # Get forecast for 2*interval hours ahead (forecast 2)
            forecast2_index = min(self.forecast_interval_hours * 2, len(hourly_temps) - 1)
            forecast2_temp = int(round(hourly_temps[forecast2_index]))
            forecast2_code = hourly_codes[forecast2_index]
            forecast2_condition = self._map_weather_code(forecast2_code, is_night, moon_phase)

            # Build DisplayData
            return DisplayData(
                timestamp=datetime.now(),
                content={
                    "type": "weather",
                    "location": self.location_name,
                    "current": {
                        "temperature": current_temp,
                        "condition": current_condition,
                        "windspeed": current_windspeed,
                        "wind_direction": current_wind_direction,
                        "units": self.units,
                        "time_label": current_time_label,
                        "aqi": aqi_value
                    },
                    "forecast1": {
                        "temperature": forecast1_temp,
                        "condition": forecast1_condition,
                        "hours_ahead": self.forecast_interval_hours,
                        "time_label": forecast1_time_label
                    },
                    "forecast2": {
                        "temperature": forecast2_temp,
                        "condition": forecast2_condition,
                        "hours_ahead": self.forecast_interval_hours * 2,
                        "time_label": forecast2_time_label
                    }
                },
                metadata={
                    "priority": "normal",
                    "suggested_display_duration": 30,
                }
            )

        except (requests.RequestException, KeyError, ValueError) as e:
            # Return error data if API call fails
            return DisplayData(
                timestamp=datetime.now(),
                content={
                    "type": "weather",
                    "error": True,
                    "error_message": "Weather API error 😢",
                    "error_details": str(e)
                },
                metadata={
                    "priority": "normal",
                    "suggested_display_duration": 30,
                }
            )

    def _map_weather_code(self, code: int, is_night: bool = False, moon_phase: float = None) -> str:
        """
        Map Open-Meteo weather code to internal condition name.

        Args:
            code: WMO weather code
            is_night: Whether it's currently nighttime
            moon_phase: Moon phase (0-1, where 0=new, 0.5=full) if nighttime

        Returns:
            Condition name (sunny, cloudy, rainy, etc.)
        """
        condition = self.WEATHER_CONDITIONS.get(code, "cloudy")

        # Replace sunny/clear with moon icon at night
        if is_night and condition == "sunny":
            # Use moon phase to determine icon
            if moon_phase is not None:
                if moon_phase < 0.1 or moon_phase > 0.9:
                    return "new_moon"  # New moon
                elif 0.4 <= moon_phase <= 0.6:
                    return "full_moon"  # Full moon
                elif moon_phase < 0.5:
                    return "waxing_moon"  # Waxing (crescent/first quarter)
                else:
                    return "waning_moon"  # Waning (last quarter/crescent)
            return "moon"  # Default moon if phase unknown

        return condition

    def _calculate_moon_phase(self, dt: datetime) -> float:
        """
        Calculate moon phase for a given datetime.

        Uses a simple astronomical algorithm based on the lunar cycle.

        Args:
            dt: Datetime to calculate phase for

        Returns:
            Moon phase as a value from 0 to 1:
            - 0.00 = New Moon
            - 0.25 = First Quarter (waxing)
            - 0.50 = Full Moon
            - 0.75 = Last Quarter (waning)
            - 1.00 = New Moon (next cycle)
        """
        # Known new moon: January 6, 2000, 18:14 UTC
        known_new_moon = datetime(2000, 1, 6, 18, 14)

        # Lunar cycle is approximately 29.53058867 days
        lunar_cycle = 29.53058867

        # Calculate days since known new moon
        days_since = (dt - known_new_moon).total_seconds() / 86400

        # Calculate phase (0 to 1)
        phase = (days_since % lunar_cycle) / lunar_cycle

        return phase

    def _format_time_compact(self, dt: datetime) -> str:
        """
        Format time in compact single-letter am/pm format.

        Examples: "3p" for 3pm, "11p" for 11pm, "12a" for midnight

        Args:
            dt: Datetime to format

        Returns:
            Compact time string (e.g., "3p", "11p", "12a")
        """
        hour = dt.hour
        if hour == 0:
            return "12a"
        elif hour < 12:
            return f"{hour}a"
        elif hour == 12:
            return "12p"
        else:
            return f"{hour - 12}p"

    def get_cache_duration(self) -> timedelta:
        """
        Cache weather data for configured duration (default: 10 minutes).

        Weather doesn't change rapidly, so we can cache safely.

        Returns:
            Cache duration
        """
        cache_seconds = self.config.get("cache_duration", 600)
        return timedelta(seconds=cache_seconds)
