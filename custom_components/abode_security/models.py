"""Data models for Abode Security."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE

from .const import LOGGER

if TYPE_CHECKING:
    from jaraco.abode.client import Client as AbodeClient


@dataclass
class AbodeSystem:
    """Abode System class."""

    abode: AbodeClient
    polling: bool
    entity_ids: set[str | None] = field(default_factory=set)
    logout_listener: CALLBACK_TYPE | None = None

    def get_test_mode(self) -> bool:
        """Get test mode status with fallback."""
        try:
            if hasattr(self.abode, "get_test_mode"):
                return self.abode.get_test_mode()
        except Exception as ex:
            LOGGER.debug("Failed to get test mode: %s", ex)
        return False

    def set_test_mode(self, enabled: bool) -> None:
        """Set test mode with fallback."""
        try:
            if hasattr(self.abode, "set_test_mode"):
                self.abode.set_test_mode(enabled)
        except Exception as ex:
            LOGGER.debug("Failed to set test mode: %s", ex)
