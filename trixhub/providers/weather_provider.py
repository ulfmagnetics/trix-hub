"""
Weather data provider using Open-Meteo API.

Fetches current weather and short-term forecast for configured location.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import requests

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
            # Build API URL
            base_url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,weathercode,windspeed_10m",
                "hourly": "temperature_2m,weathercode",
                "temperature_unit": self.units,
                "windspeed_unit": "mph",
                "forecast_days": 1,
                "timezone": "auto"
            }

            # Fetch data
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse current weather
            current_temp = int(round(data["current"]["temperature_2m"]))
            current_code = data["current"]["weathercode"]
            current_condition = self._map_weather_code(current_code)
            current_windspeed = int(round(data["current"]["windspeed_10m"]))

            # Parse hourly forecast data
            hourly_temps = data["hourly"]["temperature_2m"]
            hourly_codes = data["hourly"]["weathercode"]

            # Get forecast for interval hours ahead (forecast 1)
            forecast1_index = min(self.forecast_interval_hours, len(hourly_temps) - 1)
            forecast1_temp = int(round(hourly_temps[forecast1_index]))
            forecast1_code = hourly_codes[forecast1_index]
            forecast1_condition = self._map_weather_code(forecast1_code)

            # Get forecast for 2*interval hours ahead (forecast 2)
            forecast2_index = min(self.forecast_interval_hours * 2, len(hourly_temps) - 1)
            forecast2_temp = int(round(hourly_temps[forecast2_index]))
            forecast2_code = hourly_codes[forecast2_index]
            forecast2_condition = self._map_weather_code(forecast2_code)

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
                        "units": self.units
                    },
                    "forecast1": {
                        "temperature": forecast1_temp,
                        "condition": forecast1_condition,
                        "hours_ahead": self.forecast_interval_hours,
                    },
                    "forecast2": {
                        "temperature": forecast2_temp,
                        "condition": forecast2_condition,
                        "hours_ahead": self.forecast_interval_hours * 2,
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

    def _map_weather_code(self, code: int) -> str:
        """
        Map Open-Meteo weather code to internal condition name.

        Args:
            code: WMO weather code

        Returns:
            Condition name (sunny, cloudy, rainy, etc.)
        """
        return self.WEATHER_CONDITIONS.get(code, "cloudy")

    def get_cache_duration(self) -> timedelta:
        """
        Cache weather data for configured duration (default: 10 minutes).

        Weather doesn't change rapidly, so we can cache safely.

        Returns:
            Cache duration
        """
        cache_seconds = self.config.get("cache_duration", 600)
        return timedelta(seconds=cache_seconds)
