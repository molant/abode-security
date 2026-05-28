"""Support for the Abode Security System."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import cast

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DATE,
    ATTR_DEVICE_ID,
    ATTR_TIME,
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from . import snapshot
from .const import (
    CONF_DEBUG_LOGGING,
    CONF_ENABLE_EVENTS,
    CONF_POLLING,
    CONF_POLLING_INTERVAL,
    CONF_RETRY_COUNT,
    CONF_SNAPSHOT_RETENTION_DAYS,
    DEFAULT_ENABLE_EVENTS,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_SNAPSHOT_RETENTION_DAYS,
    DOMAIN,
    LOGGER,
)
from .services import setup_services

ATTR_DEVICE_NAME = "device_name"
ATTR_DEVICE_TYPE = "device_type"
ATTR_EVENT_CODE = "event_code"
ATTR_EVENT_NAME = "event_name"
ATTR_EVENT_TYPE = "event_type"
ATTR_EVENT_UTC = "event_utc"
ATTR_USER_NAME = "user_name"
ATTR_APP_TYPE = "app_type"
ATTR_EVENT_BY = "event_by"

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def _enable_abode_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Enable all Abode entities that were created disabled by device."""
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)

    # Find all Abode entities and enable them if disabled by device
    updated_count = 0
    for entity in entity_registry.entities.values():
        if (
            entity.config_entry_id == entry.entry_id
            and entity.platform == DOMAIN
            and entity.disabled_by == er.RegistryEntryDisabler.DEVICE
        ):
            LOGGER.debug("Enabling entity: %s", entity.entity_id)
            entity_registry.async_update_entity(entity.entity_id, disabled_by=None)
            updated_count += 1

    if updated_count > 0:
        LOGGER.info(
            "Enabled %d Abode entities that were disabled by device", updated_count
        )


PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.COVER,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up the Abode component."""
    from .websocket_api import async_register_websocket_commands

    setup_services(hass)
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Abode integration from a config entry."""
    LOGGER.info(
        "Starting Abode integration setup for user: %s",
        entry.data.get(CONF_USERNAME, "unknown"),
    )

    # Import using relative imports (proper pattern for production code)
    from . import abode
    from .abode.client import Client as Abode
    from .abode.exceptions import (
        AuthenticationException as AbodeAuthenticationException,
    )
    from .abode.exceptions import Exception as AbodeException
    from .abode.exceptions import (
        RateLimitException as AbodeRateLimitException,
    )
    from .models import AbodeSystem  # Avoid circular import

    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    polling = entry.data[CONF_POLLING]
    polling_interval = entry.data.get(CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL)
    enable_events = entry.data.get(CONF_ENABLE_EVENTS, DEFAULT_ENABLE_EVENTS)
    retry_count = entry.data.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)

    # Apply debug logging if enabled
    if entry.options.get(CONF_DEBUG_LOGGING, False):
        logging.getLogger("custom_components.abode_security").setLevel(logging.DEBUG)
        logging.getLogger("custom_components.abode_security.abode").setLevel(
            logging.DEBUG
        )
        LOGGER.info("Debug logging enabled for Abode integration")

    # Configure abode library to use config directory for storing data
    abode.config.paths.override(user_data=Path(hass.config.path("Abode")))

    # For previous config entries where unique_id is None
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=entry.data[CONF_USERNAME]
        )

    abode_client = None
    try:
        # Create client with native async support
        abode_client = Abode(username, password, False, False, False)

        # Initialize async session and perform login + device/automation fetch
        await abode_client._async_initialize()
        if not abode_client._token:
            await abode_client.login()
        if not abode_client._devices:
            await abode_client.get_devices()
        if not abode_client._automations:
            await abode_client.get_automations()

    except AbodeRateLimitException as ex:
        if abode_client:
            await abode_client.cleanup()
        cooldown = max(ex.retry_after or 30, 30)
        LOGGER.warning(
            "Abode rate limited during setup: %s. Waiting %s seconds before retry.",
            ex,
            cooldown,
        )
        await asyncio.sleep(cooldown)
        raise ConfigEntryNotReady(
            "Rate limited by Abode; will retry configuration later"
        ) from ex

    except AbodeAuthenticationException as ex:
        if abode_client:
            await abode_client.cleanup()
        raise ConfigEntryAuthFailed(f"Invalid credentials: {ex}") from ex

    except (AbodeException, aiohttp.ClientError) as ex:
        if abode_client:
            await abode_client.cleanup()
        raise ConfigEntryNotReady(f"Unable to connect to Abode: {ex}") from ex

    except Exception as ex:
        if abode_client:
            await abode_client.cleanup()
        LOGGER.error("Unexpected error during Abode setup: %s", ex, exc_info=True)
        raise

    entry.runtime_data = AbodeSystem(
        abode_client,
        polling,
        polling_interval=polling_interval,
        enable_events=enable_events,
        retry_count=retry_count,
    )

    # Set the Home Assistant event loop for thread-safe callback execution
    # This allows SocketIO callbacks to properly schedule entity updates
    loop = asyncio.get_event_loop()
    abode_client.events.set_event_loop(loop)

    # Initialize ActionManager and ConfigStore for WebSocket API.
    # Note: keys below are domain-scoped (not entry-scoped). Safe only because
    # manifest.json declares "single_config_entry": true — the framework aborts
    # any second user/discovery flow with single_instance_allowed before this
    # runs. If that flag is ever removed, these writes must move to entry.
    # runtime_data (and storage keys in ActionManager / ConfigStore namespaced
    # per entry) — see issue #5.
    from .action_manager import ActionManager
    from .action_trigger import ActionTriggerCoordinator
    from .config_store import ConfigStore
    from .scheduling.manager import ScheduleManager
    from .scheduling.store import SchedulesStore

    hass.data.setdefault(DOMAIN, {})

    action_manager = ActionManager(hass)
    await action_manager.async_setup()
    hass.data[DOMAIN]["action_manager"] = action_manager

    schedule_store = SchedulesStore(hass)
    schedule_manager = ScheduleManager(hass, schedule_store)
    await schedule_manager.async_setup()
    hass.data[DOMAIN]["schedule_manager"] = schedule_manager

    config_store = ConfigStore(hass)
    await config_store.async_load()
    hass.data[DOMAIN]["config"] = config_store.get_config()
    hass.data[DOMAIN]["config_store"] = config_store

    # Initialize ActionTriggerCoordinator
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    action_manager.set_trigger_coordinator(coordinator)
    await coordinator.async_start()
    hass.data[DOMAIN]["action_trigger"] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Enable all Abode entities that were created
    await _enable_abode_entities(hass, entry)

    await async_setup_hass_events(hass, entry)
    # setup_abode_events is synchronous - just call it directly
    setup_abode_events(hass, entry)

    # Register frontend panel for configuration
    # Note: This may fail in test environments where http/frontend aren't available
    try:
        from homeassistant.components.http import StaticPathConfig

        panel_url = "/abode_security_panel"

        # Register static path for panel JavaScript
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    url_path=panel_url,
                    path=str(Path(__file__).parent / "www"),
                    cache_headers=False,  # Disable caching during development
                )
            ]
        )

        # Register the panel in sidebar
        from homeassistant.components.frontend import async_register_built_in_panel

        async_register_built_in_panel(
            hass,
            "custom",
            sidebar_title="Abode",
            sidebar_icon="mdi:shield-home",
            frontend_url_path="abode_security",
            config={
                "_panel_custom": {
                    "name": "abode-configuration-panel",
                    "module_url": f"{panel_url}/abode-security-panel.js",
                }
            },
            require_admin=False,
        )
        LOGGER.debug("Registered Abode frontend panel")
    except Exception as ex:
        # Panel registration is optional - don't fail setup if it fails
        LOGGER.warning("Could not register frontend panel: %s", ex)

    async def _purge_callback(now: datetime) -> None:
        retention = int(
            entry.options.get(
                CONF_SNAPSHOT_RETENTION_DAYS, DEFAULT_SNAPSHOT_RETENTION_DAYS
            )
        )
        snapshot_dir = Path(hass.config.path("www/abode_security_snapshots"))
        deleted = await snapshot.async_purge_old(
            snapshot_dir, retention_days=retention, now=now
        )
        if deleted:
            LOGGER.info("Purged %d snapshot(s) older than %d days", deleted, retention)

    unsub_purge = async_track_time_interval(
        hass, _purge_callback, timedelta(days=1), cancel_on_shutdown=True
    )
    entry.async_on_unload(unsub_purge)
    # Run once on startup so a long-offline instance doesn't wait 24h for first purge.
    entry.async_create_background_task(
        hass, _purge_callback(dt_util.utcnow()), "abode_security_purge_startup"
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from .models import AbodeSystem  # Avoid circular import

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    abode_system: AbodeSystem = entry.runtime_data
    await abode_system.abode.events.stop()
    await abode_system.abode.logout()
    await abode_system.abode.cleanup()

    if abode_system.logout_listener is not None:
        abode_system.logout_listener()

    # Clean up ActionTriggerCoordinator, ActionManager, ConfigStore, ScheduleManager
    if DOMAIN in hass.data:
        if coordinator := hass.data[DOMAIN].get("action_trigger"):
            await coordinator.async_stop()
        if schedule_mgr := hass.data[DOMAIN].get("schedule_manager"):
            await schedule_mgr.async_shutdown()
        hass.data[DOMAIN].pop("action_trigger", None)
        hass.data[DOMAIN].pop("action_manager", None)
        hass.data[DOMAIN].pop("config", None)
        hass.data[DOMAIN].pop("config_store", None)
        hass.data[DOMAIN].pop("schedule_manager", None)

    return cast(bool, unload_ok)


async def async_setup_hass_events(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Home Assistant start and stop callbacks."""
    from .models import AbodeSystem  # Avoid circular import

    abode_system: AbodeSystem = entry.runtime_data
    LOGGER.info("Setting up Home Assistant events (polling=%s)", abode_system.polling)

    async def logout(_event: Event) -> None:
        """Logout of Abode."""
        if not abode_system.polling:
            await abode_system.abode.events.stop()

        await abode_system.abode.logout()
        await abode_system.abode.cleanup()
        LOGGER.info("Logged out of Abode")

    if not abode_system.polling:
        # Start socket IO event listener (async task on the HA event loop)
        LOGGER.info("Starting SocketIO task for real-time events")
        abode_system.abode.events.start()

    abode_system.logout_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, logout
    )


def setup_abode_events(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Event callbacks."""
    from .abode.helpers.timeline import Groups as GROUPS  # noqa: N814
    from .models import AbodeSystem  # Avoid circular import

    abode_system: AbodeSystem = entry.runtime_data

    def event_callback(event: str, event_json: dict[str, str]) -> None:
        """Handle an event callback from Abode."""
        data = {
            ATTR_DEVICE_ID: event_json.get(ATTR_DEVICE_ID, ""),
            ATTR_DEVICE_NAME: event_json.get(ATTR_DEVICE_NAME, ""),
            ATTR_DEVICE_TYPE: event_json.get(ATTR_DEVICE_TYPE, ""),
            ATTR_EVENT_CODE: event_json.get(ATTR_EVENT_CODE, ""),
            ATTR_EVENT_NAME: event_json.get(ATTR_EVENT_NAME, ""),
            ATTR_EVENT_TYPE: event_json.get(ATTR_EVENT_TYPE, ""),
            ATTR_EVENT_UTC: event_json.get(ATTR_EVENT_UTC, ""),
            ATTR_USER_NAME: event_json.get(ATTR_USER_NAME, ""),
            ATTR_APP_TYPE: event_json.get(ATTR_APP_TYPE, ""),
            ATTR_EVENT_BY: event_json.get(ATTR_EVENT_BY, ""),
            ATTR_DATE: event_json.get(ATTR_DATE, ""),
            ATTR_TIME: event_json.get(ATTR_TIME, ""),
        }

        hass.bus.fire(event, data)

    events = [
        GROUPS.ALARM,
        GROUPS.ALARM_END,
        GROUPS.PANEL_FAULT,
        GROUPS.PANEL_RESTORE,
        GROUPS.AUTOMATION,
        GROUPS.DISARM,
        GROUPS.ARM,
        GROUPS.ARM_FAULT,
        GROUPS.TEST,
        GROUPS.CAPTURE,
        GROUPS.DEVICE,
    ]

    for event in events:
        abode_system.abode.events.add_event_callback(
            event, partial(event_callback, event)
        )
