"""Unit tests for null-safety in service handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from custom_components.abode_security.abode.exceptions import (
    Exception as AbodeException,
)
from custom_components.abode_security.const import TRIGGERABLE_ALARM_TYPES
from custom_components.abode_security.services import (
    TRIGGER_ALARM_SCHEMA,
    _trigger_alarm_handler,
)


async def test_trigger_alarm_no_alarm_device_raises_cleanly() -> None:
    """Service must fail loudly, not crash, when `abode.get_alarm()` is None.

    Regression for #70: this once raised AttributeError when called before the
    alarm device finished loading (or on an account without one), because
    services.py called `.trigger_manual_alarm(...)` on the `Alarm | None`
    return value of `get_alarm()` without a null-check.

    The guard originally logged and returned. It now raises
    ``HomeAssistantError``: this service raises a real alarm and contacts a
    monitoring service, so a caller that gets no error is entitled to believe
    it worked. The #70 property — no AttributeError — still holds.
    """
    mock_abode = Mock()
    mock_abode.get_alarm.return_value = None
    mock_system = Mock()
    mock_system.abode = mock_abode

    mock_call = Mock()
    mock_call.hass = Mock()
    mock_call.data = {"alarm_type": "PANIC"}

    with (
        patch(
            "custom_components.abode_security.services._get_abode_system",
            return_value=mock_system,
        ),
        pytest.raises(HomeAssistantError, match="alarm"),
    ):
        await _trigger_alarm_handler(mock_call)

    mock_abode.get_alarm.assert_called_once()


async def test_trigger_alarm_propagates_api_rejection() -> None:
    """An alarm Abode refuses must surface to the caller, not just the log.

    This is the original incident's failure mode reachable through the
    service: the handler used to catch AbodeException, log it, and return
    normally, so a YAML automation calling `abode_security.trigger_alarm`
    saw success while no alarm was raised.
    """
    mock_alarm = Mock()
    mock_alarm.trigger_manual_alarm = AsyncMock(
        side_effect=AbodeException((400, '{"errorCode":16013}'))
    )
    mock_abode = Mock()
    mock_abode.get_alarm.return_value = mock_alarm
    mock_system = Mock()
    mock_system.abode = mock_abode

    mock_call = Mock()
    mock_call.hass = Mock()
    mock_call.data = {"alarm_type": "PANIC"}

    with (
        patch(
            "custom_components.abode_security.services._get_abode_system",
            return_value=mock_system,
        ),
        pytest.raises(HomeAssistantError),
    ):
        await _trigger_alarm_handler(mock_call)


def test_trigger_alarm_schema_rejects_untriggerable_types() -> None:
    """The schema, not just the UI selector, must reject them.

    `services.yaml`'s `select` only shapes the picker; a YAML automation or a
    REST/WS call bypasses it entirely.
    """
    for alarm_type in ("BURGLAR", "CO", "SMOKE", "SMOKE_CO"):
        with pytest.raises(vol.Invalid):
            TRIGGER_ALARM_SCHEMA({"alarm_type": alarm_type})

    for alarm_type in sorted(TRIGGERABLE_ALARM_TYPES):
        assert TRIGGER_ALARM_SCHEMA({"alarm_type": alarm_type})

    # Case-insensitive, since YAML authors won't reliably shout.
    assert TRIGGER_ALARM_SCHEMA({"alarm_type": "panic"})["alarm_type"] == "PANIC"


async def test_trigger_alarm_with_alarm_device_calls_through() -> None:
    """Service must still trigger the alarm normally when get_alarm() returns one.

    Sanity check that the null-guard doesn't break the happy path.
    """
    mock_alarm = Mock()
    mock_alarm.trigger_manual_alarm = AsyncMock()
    mock_abode = Mock()
    mock_abode.get_alarm.return_value = mock_alarm
    mock_system = Mock()
    mock_system.abode = mock_abode

    mock_call = Mock()
    mock_call.hass = Mock()
    mock_call.data = {"alarm_type": "PANIC"}

    with patch(
        "custom_components.abode_security.services._get_abode_system",
        return_value=mock_system,
    ):
        await _trigger_alarm_handler(mock_call)

    mock_alarm.trigger_manual_alarm.assert_awaited_once_with("PANIC")
