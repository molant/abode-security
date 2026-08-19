"""Support for the Abode Security System."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from .models import AbodeSystem

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
    from .scheduling.clock import HAClock
    from .scheduling.manager import ScheduleManager
    from .scheduling.mode_changer import HAModeChanger
    from .scheduling.scheduler import HAScheduleClock
    from .scheduling.store import SchedulesStore

    hass.data.setdefault(DOMAIN, {})

    action_manager = ActionManager(hass)
    await action_manager.async_setup()
    hass.data[DOMAIN]["action_manager"] = action_manager

    clock = HAClock(hass)
    schedule_clock = HAScheduleClock(hass)
    mode_changer = HAModeChanger(hass)
    hass.data[DOMAIN]["clock"] = clock
    hass.data[DOMAIN]["schedule_clock"] = schedule_clock
    hass.data[DOMAIN]["mode_changer"] = mode_changer

    schedule_store = SchedulesStore(hass)
    schedule_manager = ScheduleManager(
        hass, schedule_store, clock, schedule_clock, mode_changer
    )
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

    # Flag any stored action wired to an alarm Abode won't let us trigger, so
    # it surfaces as a repair issue now rather than as a silent failure during
    # the incident the action was meant to escalate. Must run *after* the
    # platforms are forwarded: the audit resolves alarm switches through the
    # entity registry, and on a first setup (or after a registry purge) it
    # would otherwise find nothing and clear a valid issue.
    action_manager.async_audit_alarm_targets()

    # Enable all Abode entities that were created
    await _enable_abode_entities(hass, entry)

    await async_setup_hass_events(hass, entry)
    # setup_abode_events is synchronous - just call it directly
    setup_abode_events(hass, entry)

    # Register frontend panel for configuration
    # Note: This may fail in test environments where http/frontend aren't available
    try:
        # HA 2026.8.0 moved this into `homeassistant.components.http.server` and
        # re-exports it here. Keep importing the package path: it is the only
        # one that resolves on the HA versions this integration supports
        # (`minimum_home_assistant_version` is 2024.1.0, and `http.server`
        # doesn't exist before 2026.8.0). pyright reads the re-export as
        # private, hence the ignore.
        from homeassistant.components.http import (
            StaticPathConfig,  # pyright: ignore[reportPrivateImportUsage]
        )

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
    # HA runs the async_on_unload callbacks only on a successful unload, and the
    # remove-after-FAILED_UNLOAD path never reaches them, so keep a handle the
    # teardown helper can cancel itself.  Cancelling twice is harmless (#206).
    hass.data[DOMAIN]["unsub_purge"] = unsub_purge
    # Run once on startup so a long-offline instance doesn't wait 24h for first purge.
    entry.async_create_background_task(
        hass, _purge_callback(dt_util.utcnow()), "abode_security_purge_startup"
    )

    return True


def _teardown_step(description: str, step: Callable[[], object]) -> None:
    """Run one synchronous teardown step, logging instead of raising.

    See :func:`_async_teardown_step` for why nothing here may propagate.
    """
    try:
        step()
    except Exception:
        LOGGER.warning("Error during Abode teardown: %s", description, exc_info=True)


async def _async_teardown_step(description: str, step: Awaitable[object]) -> None:
    """Run one awaited teardown step, logging instead of raising.

    No step may skip the ones after it: ``cleanup()`` is what closes the aiohttp
    session, and the ``hass.data`` pops are the last chance to drop the runtime.
    On the async_remove_entry path an escaping exception is worse than useless —
    HA swallows it and deletes the entry anyway, leaving a ghost schedule
    manager, action coordinator, SocketIO stream and purge timer behind with one
    ERROR line to show for it and no remaining exit short of a restart (#206).
    """
    try:
        await step
    except Exception:
        LOGGER.warning("Error during Abode teardown: %s", description, exc_info=True)


async def _async_teardown_runtime(
    hass: HomeAssistant, abode_system: AbodeSystem | None
) -> None:
    """Close the Abode session and drop every runtime object the entry owns.

    Idempotent: every step is guarded and ``abode_system`` may be ``None``, so
    running this against an entry that is already torn down is a no-op.  The
    caller resolves the runtime, which keeps the unload path strict — only
    async_remove_entry has a legitimate reason to pass ``None``.

    Every step runs through :func:`_async_teardown_step`, so one failing call
    cannot strand the rest.  Cancellation still propagates: ``CancelledError``
    is a BaseException and is not caught there.
    """
    # Quiesce the schedule manager before the Abode session is torn down.  An
    # in-flight arm/disarm would otherwise spend the rest of its retry window
    # issuing panel commands against a logged-out session, and a failure that
    # resolved in that window would still fire schedule_failed and raise the
    # repair issue (#201).
    if DOMAIN in hass.data and (
        schedule_mgr := hass.data[DOMAIN].get("schedule_manager")
    ):
        await _async_teardown_step(
            "schedule manager shutdown", schedule_mgr.async_shutdown()
        )

    if abode_system is not None:
        await _async_teardown_step(
            "event stream stop", abode_system.abode.events.stop()
        )
        # logout() only swallows ClientError/OSError, so a 4xx — a 429 from a
        # rate-limiting API being the realistic one — raises straight through.
        await _async_teardown_step("session logout", abode_system.abode.logout())
        await _async_teardown_step("client cleanup", abode_system.abode.cleanup())

        if abode_system.logout_listener is not None:
            _teardown_step("logout listener unsubscribe", abode_system.logout_listener)

    # Clean up ActionTriggerCoordinator, ActionManager, ConfigStore, ScheduleManager, clocks, mode_changer
    if DOMAIN in hass.data:
        if coordinator := hass.data[DOMAIN].get("action_trigger"):
            await _async_teardown_step(
                "action trigger coordinator stop", coordinator.async_stop()
            )
        hass.data[DOMAIN].pop("action_trigger", None)
        hass.data[DOMAIN].pop("action_manager", None)
        hass.data[DOMAIN].pop("config", None)
        hass.data[DOMAIN].pop("config_store", None)
        hass.data[DOMAIN].pop("schedule_manager", None)
        hass.data[DOMAIN].pop("clock", None)
        hass.data[DOMAIN].pop("schedule_clock", None)
        hass.data[DOMAIN].pop("mode_changer", None)
        if unsub_purge := hass.data[DOMAIN].pop("unsub_purge", None):
            _teardown_step("purge timer cancel", unsub_purge)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        # HA marks the entry FAILED_UNLOAD and leaves whatever platforms did not
        # unload holding live entities.  Tearing the session down here would
        # leave those entities pointing at a logged-out client with no SocketIO
        # stream feeding them, which is worse than staying up (#206).  The state
        # is terminal — async_unload short-circuits on it, so this function is
        # never re-entered for this entry; async_remove_entry does the cleanup
        # if the user removes the integration instead of restarting HA.
        LOGGER.warning(
            "Platform unload failed; leaving the Abode session and runtime in "
            "place so the entities still loaded keep working. Restart Home "
            "Assistant to complete the unload"
        )
        return False

    abode_system: AbodeSystem = entry.runtime_data
    await _async_teardown_runtime(hass, abode_system)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Tear down anything a failed unload left running.

    FAILED_UNLOAD is not recoverable, so async_unload_entry is never called
    again for the entry and removal is its only exit short of a restart.  The
    entities go with the entry at that point, so the runtime that #206 keeps
    alive for them must not outlive it — otherwise a remove-then-re-add without
    a restart would leave a second schedule manager, action coordinator and
    SocketIO stream running alongside the new ones.

    runtime_data is absent when the entry unloaded cleanly before removal (HA
    deletes it on the success branch), which makes this a no-op; it is present
    but half-initialised when setup failed past the point that assigns it, and
    the teardown is safe there too — logout() returns early without a token.
    """
    await _async_teardown_runtime(hass, getattr(entry, "runtime_data", None))


async def async_setup_hass_events(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Home Assistant start and stop callbacks."""
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
