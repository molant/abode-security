"""Configuration storage for Abode Security integration settings."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "abode_security_config"
STORAGE_VERSION = 1

DEFAULT_CONFIG: dict[str, Any] = {
    "debounce_seconds": 1.0,
}


class ConfigStore:
    """Persistent storage for Abode Security configuration.

    Uses Home Assistant's Store API for JSON-based persistence.
    Storage file: .storage/abode_security_config.json
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the config store."""
        self._hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._config: dict[str, Any] = DEFAULT_CONFIG.copy()

    async def async_load(self) -> None:
        """Load config from storage.

        Handles missing file by using default config.
        """
        data = await self._store.async_load()
        if data is None:
            self._config = DEFAULT_CONFIG.copy()
            return

        # Merge with defaults to handle new config keys
        self._config = {**DEFAULT_CONFIG, **data}

    async def async_save(self) -> None:
        """Save config to storage."""
        await self._store.async_save(self._config)

    def get_config(self) -> dict[str, Any]:
        """Get the current configuration."""
        return self._config.copy()

    async def async_set(self, key: str, value: Any) -> dict[str, Any]:
        """Set a configuration value and persist.

        Args:
            key: Configuration key
            value: Configuration value

        Returns:
            The updated configuration

        Raises:
            ValueError: If the key is not a valid configuration key
        """
        if key not in DEFAULT_CONFIG:
            raise ValueError(f"Unknown configuration key: {key}")

        self._config[key] = value
        await self.async_save()
        return self.get_config()

    async def async_update(self, **kwargs: Any) -> dict[str, Any]:
        """Update multiple configuration values and persist.

        Args:
            **kwargs: Configuration key-value pairs

        Returns:
            The updated configuration

        Raises:
            ValueError: If any key is not a valid configuration key
        """
        for key in kwargs:
            if key not in DEFAULT_CONFIG:
                raise ValueError(f"Unknown configuration key: {key}")

        self._config.update(kwargs)
        await self.async_save()
        return self.get_config()
