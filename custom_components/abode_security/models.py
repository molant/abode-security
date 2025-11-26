"""Data models for Abode Security."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE

from .const import (
    CONF_ENABLE_EVENTS,
    CONF_POLLING_INTERVAL,
    DEFAULT_ENABLE_EVENTS,
    DEFAULT_EVENT_FILTER,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_RETRY_COUNT,
    EVENT_TYPES,
    LOGGER,
)

if TYPE_CHECKING:
    from abode.client import Client as AbodeClient

# Configuration Presets
POLLING_PRESETS = {
    "aggressive": {
        CONF_POLLING_INTERVAL: 15,
        CONF_ENABLE_EVENTS: True,
        "description": "Real-time updates - higher API load",
    },
    "balanced": {
        CONF_POLLING_INTERVAL: 30,
        CONF_ENABLE_EVENTS: True,
        "description": "Balanced performance - recommended",
    },
    "conservative": {
        CONF_POLLING_INTERVAL: 60,
        CONF_ENABLE_EVENTS: False,
        "description": "Low API load - delayed updates",
    },
    "event_based": {
        CONF_POLLING_INTERVAL: 120,
        CONF_ENABLE_EVENTS: True,
        "description": "Event-driven updates - minimal polling",
    },
}


@dataclass
class PollingStats:
    """Polling statistics."""

    last_update: datetime = field(default_factory=lambda: datetime.now(UTC))
    update_count: int = 0
    error_count: int = 0
    average_duration: float = 0.0
    total_duration: float = 0.0

    def record_update(self, duration: float) -> None:
        """Record a successful update."""
        self.update_count += 1
        self.total_duration += duration
        self.average_duration = self.total_duration / self.update_count
        self.last_update = datetime.now(UTC)

    def record_error(self) -> None:
        """Record a failed update."""
        self.error_count += 1
        self.last_update = datetime.now(UTC)

    def reset(self) -> None:
        """Reset all statistics."""
        self.update_count = 0
        self.error_count = 0
        self.average_duration = 0.0
        self.total_duration = 0.0
        self.last_update = datetime.now(UTC)


class EventFilter:
    """Filter events based on type."""

    def __init__(self, filter_types: list[str] | None = None) -> None:
        """Initialize event filter."""
        # If no filter specified, allow all events
        self.filter_types = filter_types if filter_types else EVENT_TYPES
        self.filtered_count = 0
        self.allowed_count = 0

    def should_process(self, event_type: str) -> bool:
        """Check if event type should be processed."""
        if event_type not in self.filter_types:
            self.filtered_count += 1
            LOGGER.debug("EventFilter: Filtered event type '%s'", event_type)
            return False

        self.allowed_count += 1
        return True

    def get_stats(self) -> dict[str, int]:
        """Get filter statistics."""
        return {
            "filtered": self.filtered_count,
            "allowed": self.allowed_count,
            "total": self.filtered_count + self.allowed_count,
        }

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.filtered_count = 0
        self.allowed_count = 0


class SmartPolling:
    """Smart polling that adapts based on system activity."""

    def __init__(self, base_interval: int) -> None:
        """Initialize smart polling."""
        self.base_interval = base_interval
        self.stats = PollingStats()

    def get_optimal_interval(self) -> int:
        """Calculate optimal polling interval based on statistics."""
        # Back off on errors
        if self.stats.error_count > 5:
            adjusted = min(self.base_interval * 2, 120)
            LOGGER.debug(
                "SmartPolling: Backing off due to %d errors (interval: %d → %d)",
                self.stats.error_count,
                self.base_interval,
                adjusted,
            )
            return adjusted

        # Slow down if API is slow
        if self.stats.average_duration > 5.0:
            adjusted = min(self.base_interval + 15, 120)
            LOGGER.debug(
                "SmartPolling: Slowing down due to slow API (duration: %.2fs, interval: %d → %d)",
                self.stats.average_duration,
                self.base_interval,
                adjusted,
            )
            return adjusted

        # Speed up if performing well
        if self.stats.error_count == 0 and self.stats.average_duration < 1.0:
            adjusted = max(self.base_interval - 5, 15)
            if adjusted < self.base_interval:
                LOGGER.debug(
                    "SmartPolling: Speeding up due to good performance (interval: %d → %d)",
                    self.base_interval,
                    adjusted,
                )
                return adjusted

        return self.base_interval

    def record_update(self, duration: float) -> None:
        """Record a successful update."""
        self.stats.record_update(duration)

    def record_error(self) -> None:
        """Record a failed update."""
        self.stats.record_error()

    def reset_stats(self) -> None:
        """Reset statistics."""
        self.stats.reset()


@dataclass
class AbodeSystem:
    """Abode System class."""

    abode: AbodeClient
    polling: bool
    entity_ids: set[str | None] = field(default_factory=set)
    logout_listener: CALLBACK_TYPE | None = None
    polling_interval: int = DEFAULT_POLLING_INTERVAL
    enable_events: bool = DEFAULT_ENABLE_EVENTS
    retry_count: int = DEFAULT_RETRY_COUNT
    event_filter_types: list[str] = field(default_factory=lambda: DEFAULT_EVENT_FILTER)
    smart_polling: SmartPolling | None = field(default=None, init=False)
    event_filter: EventFilter | None = field(default=None, init=False)
    test_mode_supported: bool = field(default=True, init=False)
    cms_settings_supported: bool = field(default=True, init=False)
    cms_settings_cache: dict = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Initialize smart polling and event filter after dataclass init."""
        self.smart_polling = SmartPolling(self.polling_interval)
        self.event_filter = EventFilter(
            self.event_filter_types if self.event_filter_types else None
        )

    async def get_test_mode(self) -> bool:
        """Get test mode status with fallback."""
        try:
            result = await self.abode.get_test_mode()
            LOGGER.debug("get_test_mode() returned: %s (type: %s)", result, type(result))
            self.test_mode_supported = getattr(self.abode, "test_mode_supported", True)
            return result
        except AttributeError:
            LOGGER.debug("get_test_mode method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get test mode: %s", ex)
            self.test_mode_supported = getattr(self.abode, "test_mode_supported", False)
            return False

    async def set_test_mode(self, enabled: bool) -> None:
        """Set test mode with fallback."""
        try:
            await self.abode.set_test_mode(enabled)
            LOGGER.info("Test mode %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_test_mode method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set test mode: %s", ex)

    async def get_monitoring_active(self) -> bool:
        """Get monitoring active status with fallback."""
        try:
            cms_settings = await self.abode.get_cms_settings()
            result = cms_settings.get("monitoringActive", False)
            LOGGER.debug("get_monitoring_active() returned: %s", result)
            self.cms_settings_supported = True
            self.cms_settings_cache = cms_settings
            return bool(result)
        except AttributeError:
            LOGGER.debug("get_cms_settings method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get monitoring active: %s", ex)
            self.cms_settings_supported = False
            return False

    async def set_monitoring_active(self, enabled: bool) -> None:
        """Set monitoring active with fallback."""
        try:
            await self.abode.set_cms_setting("monitoringActive", enabled)
            LOGGER.info("Monitoring active %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_cms_setting method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set monitoring active: %s", ex)

    async def get_send_media(self) -> bool:
        """Get send media status with fallback."""
        try:
            cms_settings = await self.abode.get_cms_settings()
            result = cms_settings.get("sendMedia", False)
            LOGGER.debug("get_send_media() returned: %s", result)
            self.cms_settings_supported = True
            self.cms_settings_cache = cms_settings
            return bool(result)
        except AttributeError:
            LOGGER.debug("get_cms_settings method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get send media: %s", ex)
            self.cms_settings_supported = False
            return False

    async def set_send_media(self, enabled: bool) -> None:
        """Set send media with fallback."""
        try:
            await self.abode.set_cms_setting("sendMedia", enabled)
            LOGGER.info("Send media %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_cms_setting method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set send media: %s", ex)

    async def get_dispatch_without_verification(self) -> bool:
        """Get dispatch without verification status with fallback."""
        try:
            cms_settings = await self.abode.get_cms_settings()
            result = cms_settings.get("dispatchWithoutVerification", False)
            LOGGER.debug("get_dispatch_without_verification() returned: %s", result)
            self.cms_settings_supported = True
            self.cms_settings_cache = cms_settings
            return bool(result)
        except AttributeError:
            LOGGER.debug("get_cms_settings method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get dispatch without verification: %s", ex)
            self.cms_settings_supported = False
            return False

    async def set_dispatch_without_verification(self, enabled: bool) -> None:
        """Set dispatch without verification with fallback."""
        try:
            await self.abode.set_cms_setting("dispatchWithoutVerification", enabled)
            LOGGER.info("Dispatch without verification %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_cms_setting method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set dispatch without verification: %s", ex)

    async def get_dispatch_police(self) -> bool:
        """Get dispatch police status with fallback."""
        try:
            cms_settings = await self.abode.get_cms_settings()
            result = cms_settings.get("dispatchPolice", False)
            LOGGER.debug("get_dispatch_police() returned: %s", result)
            self.cms_settings_supported = True
            self.cms_settings_cache = cms_settings
            return bool(result)
        except AttributeError:
            LOGGER.debug("get_cms_settings method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get dispatch police: %s", ex)
            self.cms_settings_supported = False
            return False

    async def set_dispatch_police(self, enabled: bool) -> None:
        """Set dispatch police with fallback."""
        try:
            await self.abode.set_cms_setting("dispatchPolice", enabled)
            LOGGER.info("Dispatch police %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_cms_setting method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set dispatch police: %s", ex)

    async def get_dispatch_fire(self) -> bool:
        """Get dispatch fire status with fallback."""
        try:
            cms_settings = await self.abode.get_cms_settings()
            result = cms_settings.get("dispatchFire", False)
            LOGGER.debug("get_dispatch_fire() returned: %s", result)
            self.cms_settings_supported = True
            self.cms_settings_cache = cms_settings
            return bool(result)
        except AttributeError:
            LOGGER.debug("get_cms_settings method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get dispatch fire: %s", ex)
            self.cms_settings_supported = False
            return False

    async def set_dispatch_fire(self, enabled: bool) -> None:
        """Set dispatch fire with fallback."""
        try:
            await self.abode.set_cms_setting("dispatchFire", enabled)
            LOGGER.info("Dispatch fire %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_cms_setting method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set dispatch fire: %s", ex)

    async def get_dispatch_medical(self) -> bool:
        """Get dispatch medical status with fallback."""
        try:
            cms_settings = await self.abode.get_cms_settings()
            result = cms_settings.get("dispatchMedical", False)
            LOGGER.debug("get_dispatch_medical() returned: %s", result)
            self.cms_settings_supported = True
            self.cms_settings_cache = cms_settings
            return bool(result)
        except AttributeError:
            LOGGER.debug("get_cms_settings method not available in abode client")
            return False
        except Exception as ex:
            LOGGER.warning("Failed to get dispatch medical: %s", ex)
            self.cms_settings_supported = False
            return False

    async def set_dispatch_medical(self, enabled: bool) -> None:
        """Set dispatch medical with fallback."""
        try:
            await self.abode.set_cms_setting("dispatchMedical", enabled)
            LOGGER.info("Dispatch medical %s", "enabled" if enabled else "disabled")
        except AttributeError:
            LOGGER.debug("set_cms_setting method not available in abode client")
        except Exception as ex:
            LOGGER.debug("Failed to set dispatch medical: %s", ex)
