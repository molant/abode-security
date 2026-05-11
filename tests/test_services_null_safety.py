"""Unit tests for null-safety in service handlers."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.abode_security.services import _trigger_alarm_handler


async def test_trigger_alarm_no_alarm_device_logs_and_returns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Service must not crash when `abode.get_alarm()` returns None.

    Regression for #70: previously raised AttributeError when called before
    the alarm device finished loading (or on accounts without one), because
    services.py called `.trigger_manual_alarm(...)` on the `Alarm | None`
    return value of `get_alarm()` without a null-check.
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
        caplog.at_level(logging.ERROR, logger="custom_components.abode_security"),
    ):
        await _trigger_alarm_handler(mock_call)

    mock_abode.get_alarm.assert_called_once()
    assert any(
        "alarm" in record.message.lower() and record.levelno >= logging.ERROR
        for record in caplog.records
    ), f"Expected an error-level log mentioning 'alarm', got: {caplog.records!r}"


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
