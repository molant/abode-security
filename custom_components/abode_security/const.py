"""Constants for the Abode Security System component."""

import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "abode_security"
ATTRIBUTION = "Data provided by goabode.com"

# Configuration keys
CONF_POLLING = "polling"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_ENABLE_EVENTS = "enable_events"
CONF_RETRY_COUNT = "retry_count"
CONF_EVENT_FILTER = "event_filter"

# Default configuration values
DEFAULT_POLLING_INTERVAL = 30  # seconds
DEFAULT_ENABLE_EVENTS = True
DEFAULT_RETRY_COUNT = 3
DEFAULT_EVENT_FILTER: list[str] = []  # No filtering by default

# Event types for filtering
EVENT_TYPES = [
    "device_update",
    "device_add",
    "device_remove",
    "alarm_state_change",
    "automation_trigger",
    "test_mode_change",
    "battery_warning",
]
