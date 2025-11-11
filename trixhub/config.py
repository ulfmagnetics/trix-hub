"""
Configuration loader for trix-hub.

Loads settings from config.json with sensible defaults.
"""

import json
import os
from typing import Any, Dict


# Default configuration
DEFAULT_CONFIG = {
    "providers": {
        "weather": {
            "enabled": True,
            "location": {
                "latitude": 40.0,
                "longitude": -80.0,
                "name": "Pittsburgh, PA"
            },
            "units": "fahrenheit",
            "forecast_hours": 3,
            "cache_duration": 600
        },
        "time": {
            "enabled": True,
            "timezone": "America/New_York",
            "format_12h": True
        }
    }
}


class Config:
    """
    Configuration manager for trix-hub.

    Loads config.json from project root, falling back to defaults.
    """

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file (default: config.json in current directory)
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.

        Returns:
            Configuration dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {self.config_path}: {e}")
                print("Using default configuration")
                return DEFAULT_CONFIG.copy()
        else:
            # Config file doesn't exist, use defaults
            return DEFAULT_CONFIG.copy()

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get nested config value.

        Args:
            *keys: Nested keys to traverse (e.g., "providers", "weather", "location")
            default: Default value if key not found

        Returns:
            Config value or default

        Example:
            config.get("providers", "weather", "location", "latitude")
            # Returns: 40.0
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of provider (e.g., "weather", "time")

        Returns:
            Provider configuration dictionary (empty dict if not found)
        """
        return self.get("providers", provider_name, default={})

    def get_matrix_config(self) -> Dict[str, Any]:
        """
        Get Matrix Portal configuration.

        Returns:
            Matrix configuration dictionary with server_hostname, width, height, output_dir
        """
        return self.get("matrix", default={
            "server_hostname": "http://trix-server.local",
            "width": 64,
            "height": 32,
            "output_dir": "output"
        })

    def get_scheduler_config(self) -> Dict[str, Any]:
        """
        Get scheduler configuration.

        Returns:
            Scheduler configuration dictionary with mode, default_display_duration, provider_rotation
        """
        return self.get("scheduler", default={
            "mode": "simple_rotation",
            "default_display_duration": 30,
            "provider_rotation": []
        })


# Global config instance
_config = None


def get_config() -> Config:
    """
    Get global configuration instance.

    Lazy-loads configuration on first access.

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
