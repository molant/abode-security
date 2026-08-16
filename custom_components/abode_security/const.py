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
CONF_DEBUG_LOGGING = "debug_logging"
CONF_SNAPSHOT_RETENTION_DAYS = "snapshot_retention_days"

# Default configuration values
DEFAULT_POLLING_INTERVAL = 30  # seconds
DEFAULT_ENABLE_EVENTS = True
DEFAULT_RETRY_COUNT = 3
DEFAULT_EVENT_FILTER: list[str] = []  # No filtering by default
DEFAULT_SNAPSHOT_RETENTION_DAYS = 30

# Schedules storage
STORAGE_KEY_SCHEDULES = "abode_security_schedules"
STORAGE_VERSION_SCHEDULES = 1
REPAIR_ISSUE_CORRUPT_SCHEDULES = "corrupt_schedule_records"
MAX_SCHEDULE_NAME_LENGTH = 100
MAX_SCHEDULES = 50
CONTEXT_ID_PREFIX = "abode_sched_"

# Schedule retry policy
SCHEDULE_RETRY_DELAYS_SECONDS = (1, 4, 16)  # delays between attempts
SCHEDULE_RETRY_TOTAL_ATTEMPTS = (
    4  # 1 initial + 3 retries; must equal len(SCHEDULE_RETRY_DELAYS_SECONDS) + 1
)

# Schedule HA events
EVENT_SCHEDULE_FIRED = "abode_security.schedule_fired"
EVENT_SCHEDULE_SKIPPED = "abode_security.schedule_skipped"
EVENT_SCHEDULE_FAILED = "abode_security.schedule_failed"
REPAIR_ISSUE_SCHEDULE_FIRE_FAILED = "schedule_fire_failed"

# Actions repair issues
REPAIR_ISSUE_ACTION_ALARM_FAILED = "action_alarm_failed"
REPAIR_ISSUE_UNTRIGGERABLE_ALARM = "action_untriggerable_alarm"

# Abode's POST /integrations/v1/panel/alarm only accepts these three types.
# CO / SMOKE / SMOKE_CO / BURGLAR are inbound classifications reported by
# sensors; asking the API to raise one returns 400 errorCode 16013
# ("invalid {{param}} value"). Confirmed against the official Abode Android
# app, whose manual-alarm screen only ever triggers Panic/Silent/Medical.
TRIGGERABLE_ALARM_TYPES = frozenset({"PANIC", "SILENT_PANIC", "MEDICAL"})

# The domain an action's alarm targets must live in. Actions arm their alarms
# with `switch.turn_on`, and Home Assistant silently drops entities outside the
# service's own domain instead of raising — so the pre-flight guard in
# `action_trigger.async_arm_alarm` and the service call it protects must always
# name the same domain. Kept here as one constant so they cannot drift apart,
# and so `action_manager.async_audit_alarm_targets` flags the same mismatch
# before an action ever fires.
ALARM_SWITCH_DOMAIN = "switch"

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
