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

# Default configuration values
DEFAULT_POLLING_INTERVAL = 30  # seconds
DEFAULT_ENABLE_EVENTS = True
DEFAULT_RETRY_COUNT = 3
