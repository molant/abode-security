"""Tests for the Abode Security module."""

import logging
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.abode_security.abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
)
from custom_components.abode_security.abode.exceptions import (
    Exception as AbodeException,
)
from custom_components.abode_security.const import (
    CONF_SNAPSHOT_RETENTION_DAYS,
    DEFAULT_SNAPSHOT_RETENTION_DAYS,
    DOMAIN,
)
from custom_components.abode_security.scheduling.manager import ScheduleManager
from custom_components.abode_security.services import SERVICE_SETTINGS

from .common import setup_platform


async def test_change_settings(hass: HomeAssistant, mock_abode) -> None:
    """Test change_setting service."""
    await setup_platform(hass, ALARM_DOMAIN)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SETTINGS,
        {"setting": "confirm_snd", "value": "loud"},
        blocking=True,
    )
    await hass.async_block_till_done()
    mock_abode.set_setting.assert_called_once()


async def test_add_unique_id(hass: HomeAssistant, mock_abode) -> None:
    """Test unique_id is set to Abode username."""
    del mock_abode  # Fixture dependency, not used directly
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)
    # Set unique_id to None to match previous config entries
    hass.config_entries.async_update_entry(entry=mock_entry, unique_id=None)
    await hass.async_block_till_done()

    assert mock_entry.unique_id is None

    await hass.config_entries.async_reload(mock_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_entry.unique_id == mock_entry.data[CONF_USERNAME]


async def test_unload_entry(hass: HomeAssistant, mock_abode) -> None:
    """Test unloading the Abode Security entry."""
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)

    assert await hass.config_entries.async_unload(mock_entry.entry_id)
    mock_abode.logout.assert_called_once()
    mock_abode.events.stop.assert_called_once()


async def test_unload_quiesces_schedules_before_the_session(
    hass: HomeAssistant, mock_abode
) -> None:
    """The schedule manager must be shut down before the Abode session is.

    Otherwise an in-flight arm/disarm spends the rest of its retry window
    issuing panel commands against a logged-out session, and a failure that
    resolves inside that window still fires schedule_failed and raises the
    repair issue (#201).  Ordering is the whole point of the fix, so assert the
    order and not merely that shutdown was called.
    """
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)

    order: list[str] = []
    real_shutdown = ScheduleManager.async_shutdown

    async def _tracked_shutdown(self: ScheduleManager) -> None:
        order.append("schedules")
        await real_shutdown(self)

    # Both are awaited with no arguments by async_unload_entry.
    mock_abode.events.stop.side_effect = lambda: order.append("events")
    mock_abode.logout.side_effect = lambda: order.append("logout")

    with patch.object(ScheduleManager, "async_shutdown", _tracked_shutdown):
        assert await hass.config_entries.async_unload(mock_entry.entry_id)

    assert order == ["schedules", "events", "logout"]


async def test_invalid_credentials(hass: HomeAssistant) -> None:
    """Test Abode Security credentials changing."""
    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.BAD_REQUEST, "auth error")
        ),
    ):
        config_entry = await setup_platform(hass, ALARM_DOMAIN)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"

    hass.config_entries.flow.async_abort(flows[0]["flow_id"])
    assert not hass.config_entries.flow.async_progress()


async def test_raise_config_entry_not_ready_when_offline(hass: HomeAssistant) -> None:
    """Config entry state is SETUP_RETRY when abode is offline."""
    with patch(
        "custom_components.abode_security.abode.client.Client",
        side_effect=AbodeException("any"),
    ):
        config_entry = await setup_platform(hass, ALARM_DOMAIN)
        await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    assert hass.config_entries.flow.async_progress() == []


async def test_purge_task_fires_after_daily_interval(
    hass: HomeAssistant, mock_abode: object
) -> None:
    """Daily purge callback invokes async_purge_old after the interval elapses."""
    del mock_abode
    purge_mock = AsyncMock(return_value=0)
    with patch("custom_components.abode_security.snapshot.async_purge_old", purge_mock):
        await setup_platform(hass, ALARM_DOMAIN)
        await hass.async_block_till_done()
        # Startup call already ran; reset so we only count the timer-fired call.
        purge_mock.reset_mock()

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=25))
        await hass.async_block_till_done()

    purge_mock.assert_called_once()
    _kw = purge_mock.call_args.kwargs
    assert _kw["retention_days"] == DEFAULT_SNAPSHOT_RETENTION_DAYS


async def test_purge_task_uses_configured_retention(
    hass: HomeAssistant, mock_abode: object
) -> None:
    """Purge uses the retention days from entry options when set."""
    del mock_abode
    purge_mock = AsyncMock(return_value=0)
    with patch("custom_components.abode_security.snapshot.async_purge_old", purge_mock):
        mock_entry = await setup_platform(hass, ALARM_DOMAIN)
        hass.config_entries.async_update_entry(
            mock_entry, options={CONF_SNAPSHOT_RETENTION_DAYS: 60}
        )
        await hass.async_block_till_done()
        purge_mock.reset_mock()

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=25))
        await hass.async_block_till_done()

    purge_mock.assert_called_once()
    assert purge_mock.call_args.kwargs["retention_days"] == 60


async def test_purge_timer_cancelled_on_unload(
    hass: HomeAssistant, mock_abode: object
) -> None:
    """Purge timer is cancelled when the config entry is unloaded."""
    del mock_abode
    purge_mock = AsyncMock(return_value=0)
    with patch("custom_components.abode_security.snapshot.async_purge_old", purge_mock):
        mock_entry = await setup_platform(hass, ALARM_DOMAIN)
        await hass.async_block_till_done()
        purge_mock.reset_mock()

        assert await hass.config_entries.async_unload(mock_entry.entry_id)
        await hass.async_block_till_done()

        # After unload the timer must not fire.
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=25))
        await hass.async_block_till_done()

    purge_mock.assert_not_called()


async def test_failed_platform_unload_leaves_runtime_intact(
    hass: HomeAssistant, mock_abode, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed platform unload must not tear the Abode runtime down.

    HA marks the entry FAILED_UNLOAD but its platforms keep holding live
    entities, so logging the session out, stopping the SocketIO stream or
    popping the runtime objects would leave those entities pointing at a dead
    session (#206).  The success path is covered by ``test_unload_entry`` and
    ``test_unload_quiesces_schedules_before_the_session``; the pair is what
    covers the gate.
    """
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)
    runtime_before = dict(hass.data[DOMAIN])
    assert hass.states.get("alarm_control_panel.test_alarm") is not None

    shutdown = AsyncMock()
    with (
        patch.object(
            hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
        ),
        patch.object(ScheduleManager, "async_shutdown", shutdown),
        caplog.at_level(logging.WARNING, logger="custom_components.abode_security"),
    ):
        assert not await hass.config_entries.async_unload(mock_entry.entry_id)

    assert mock_entry.state is ConfigEntryState.FAILED_UNLOAD
    assert "Platform unload failed" in caplog.text

    shutdown.assert_not_called()
    mock_abode.events.stop.assert_not_called()
    mock_abode.logout.assert_not_called()
    mock_abode.cleanup.assert_not_called()

    # The entity the fix exists for is still alive, and so is everything it
    # talks to — assert the whole mapping so a future pop added outside the
    # guard cannot slip through.
    assert hass.states.get("alarm_control_panel.test_alarm") is not None
    assert hass.data[DOMAIN] == runtime_before
    assert hass.config_entries.async_get_entry(mock_entry.entry_id) is not None
    assert mock_entry.runtime_data is not None


async def test_removing_an_entry_after_a_failed_unload_tears_the_runtime_down(
    hass: HomeAssistant, mock_abode
) -> None:
    """Removal is the only exit from FAILED_UNLOAD short of a restart (#206).

    The entities go with the entry, so the runtime kept alive for them must not
    outlive it — otherwise a remove-then-re-add without a restart leaves a
    second schedule manager and SocketIO stream running alongside the new ones.
    """
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)

    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert not await hass.config_entries.async_unload(mock_entry.entry_id)

    assert mock_entry.state is ConfigEntryState.FAILED_UNLOAD
    # Pin the precondition: the runtime is still up at this point, so the
    # assertions below can only be satisfied by async_remove_entry.
    mock_abode.logout.assert_not_called()

    assert await hass.config_entries.async_remove(mock_entry.entry_id) == {
        "require_restart": True
    }
    await hass.async_block_till_done()

    mock_abode.events.stop.assert_called_once()
    mock_abode.logout.assert_called_once()
    mock_abode.cleanup.assert_called_once()
    for key in ("schedule_manager", "action_trigger", "config_store"):
        assert key not in hass.data[DOMAIN]

    # The daily purge timer is registered with entry.async_on_unload, and HA
    # runs those callbacks only on a successful unload — never on this path —
    # so the teardown has to cancel it or it keeps firing against the options
    # of an entry that no longer exists.
    purge_mock = AsyncMock(return_value=0)
    with patch("custom_components.abode_security.snapshot.async_purge_old", purge_mock):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=25))
        await hass.async_block_till_done()
    purge_mock.assert_not_called()


async def test_removing_a_cleanly_unloaded_entry_is_a_no_op(
    hass: HomeAssistant, mock_abode, caplog: pytest.LogCaptureFixture
) -> None:
    """async_remove_entry must tolerate an entry whose runtime is already gone.

    A normal remove unloads first, which deletes ``runtime_data`` and empties
    hass.data, so the teardown helper runs a second time against nothing.
    """
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)

    # ConfigEntry.async_remove swallows exceptions from async_remove_entry and
    # only logs them, so a helper that blew up on the already-empty runtime
    # would leave every other assertion here green.  Watch the log instead.
    with caplog.at_level(logging.ERROR, logger="homeassistant.config_entries"):
        assert await hass.config_entries.async_remove(mock_entry.entry_id) == {
            "require_restart": False
        }
        await hass.async_block_till_done()

    assert "Error calling entry remove callback" not in caplog.text
    mock_abode.logout.assert_called_once()
    assert not hasattr(mock_entry, "runtime_data")


async def test_removing_an_entry_whose_setup_failed_late_is_safe(
    hass: HomeAssistant, mock_abode, caplog: pytest.LogCaptureFixture
) -> None:
    """The third entry point into the teardown: removal from a failed setup.

    HA keeps ``runtime_data`` when ``async_unload`` short-circuits on a
    non-LOADED state, so a setup that failed *after* it was assigned leaves a
    half-initialised AbodeSystem attached and ``async_remove_entry`` tears it
    down.  Nothing else closes the aiohttp session on that path, and anything
    the teardown raised would be swallowed by HA and skip the rest of it (#206).
    """
    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        AsyncMock(side_effect=RuntimeError("boom")),
    ):
        mock_entry = await setup_platform(hass, ALARM_DOMAIN)

    assert mock_entry.state is ConfigEntryState.SETUP_ERROR
    # The precondition the docstring rests on: setup got far enough to attach a
    # runtime, so the teardown really does run against a half-built one.
    assert hasattr(mock_entry, "runtime_data")

    with caplog.at_level(logging.ERROR, logger="homeassistant.config_entries"):
        await hass.config_entries.async_remove(mock_entry.entry_id)
        await hass.async_block_till_done()

    # Not just "it did not raise" — the teardown has to have run to completion.
    assert "Error calling entry remove callback" not in caplog.text
    mock_abode.cleanup.assert_called_once()
    for key in ("schedule_manager", "action_trigger", "config_store"):
        assert key not in hass.data[DOMAIN]


async def test_teardown_completes_when_the_abode_session_fails_to_close(
    hass: HomeAssistant, mock_abode, caplog: pytest.LogCaptureFixture
) -> None:
    """One failing teardown step must not strand the rest of the teardown.

    ``logout()`` only swallows ClientError/OSError, so a 429 from Abode's
    rate-limited API raises through.  On the async_remove_entry path HA swallows
    whatever escapes and deletes the entry anyway, so an abort there would leave
    a ghost runtime and purge timer with no exit short of a restart (#206).
    """
    mock_entry = await setup_platform(hass, ALARM_DOMAIN)
    mock_abode.logout.side_effect = AbodeException("rate limited")

    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert not await hass.config_entries.async_unload(mock_entry.entry_id)

    with caplog.at_level(logging.WARNING, logger="custom_components.abode_security"):
        assert await hass.config_entries.async_remove(mock_entry.entry_id) == {
            "require_restart": True
        }
        await hass.async_block_till_done()

    assert "Error during Abode teardown: session logout" in caplog.text

    # Everything after the failing step still ran.
    mock_abode.cleanup.assert_called_once()
    for key in ("schedule_manager", "action_trigger", "config_store"):
        assert key not in hass.data[DOMAIN]

    purge_mock = AsyncMock(return_value=0)
    with patch("custom_components.abode_security.snapshot.async_purge_old", purge_mock):
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(hours=25))
        await hass.async_block_till_done()
    purge_mock.assert_not_called()
