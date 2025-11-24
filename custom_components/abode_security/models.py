"""Data models for Abode Security."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from homeassistant.core import CALLBACK_TYPE

from .const import (
    CONF_ENABLE_EVENTS,
    CONF_EVENT_FILTER,
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

    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    update_count: int = 0
    error_count: int = 0
    average_duration: float = 0.0
    total_duration: float = 0.0

    def record_update(self, duration: float) -> None:
        """Record a successful update."""
        self.update_count += 1
        self.total_duration += duration
        self.average_duration = self.total_duration / self.update_count
        self.last_update = datetime.now(timezone.utc)

    def record_error(self) -> None:
        """Record a failed update."""
        self.error_count += 1
        self.last_update = datetime.now(timezone.utc)

    def reset(self) -> None:
        """Reset all statistics."""
        self.update_count = 0
        self.error_count = 0
        self.average_duration = 0.0
        self.total_duration = 0.0
        self.last_update = datetime.now(timezone.utc)


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

    def __post_init__(self) -> None:
        """Initialize smart polling and event filter after dataclass init."""
        self.smart_polling = SmartPolling(self.polling_interval)
        self.event_filter = EventFilter(
            self.event_filter_types if self.event_filter_types else None
        )

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
