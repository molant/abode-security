"""Tests for the Abode Security module."""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

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
