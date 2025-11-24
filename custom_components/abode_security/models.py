"""Data models for Abode Security."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE

from .const import LOGGER
from .decorators import handle_abode_errors

if TYPE_CHECKING:
    from abode.client import Client as AbodeClient


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
            result = self.abode.get_test_mode()
            LOGGER.debug("get_test_mode() returned: %s (type: %s)", result, type(result))
            return result
        except AttributeError:
            LOGGER.debug("get_test_mode method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get test mode: %s", ex)
            return False

    def set_test_mode(self, enabled: bool) -> None:
        """Set test mode with fallback."""
        try:
            self.abode.set_test_mode(enabled)
            LOGGER.info("Test mode %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_test_mode method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set test mode: %s", ex)
