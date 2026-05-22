"""Unit tests for the fire_test_notification service handler.

The coordinator method is exercised in test_action_trigger.py — these tests
cover the thin service-layer shim: the debug_logging opt-in gate and the
coordinator-not-ready early return.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.abode_security.const import CONF_DEBUG_LOGGING, DOMAIN
from custom_components.abode_security.services import _fire_test_notification


def _make_call(
    *,
    debug_logging: bool,
    coordinator: object | None,
    data: dict[str, str] | None = None,
) -> Mock:
    """Build a Mock ServiceCall with a hass that mimics options + hass.data."""
    entry = Mock()
    entry.options = {CONF_DEBUG_LOGGING: debug_logging}

    config_entries = Mock()
    config_entries.async_entries.return_value = [entry]

    hass = Mock()
    hass.config_entries = config_entries
    hass.data = (
        {DOMAIN: {}}
        if coordinator is None
        else {DOMAIN: {"action_trigger": coordinator}}
    )

    call = Mock()
    call.hass = hass
    call.data = data or {
        "action_id": "00000000-0000-0000-0000-000000000000",
        "sensor_entity_id": "binary_sensor.front_door",
        "mode": "home",
    }
    return call


async def test_refuses_when_debug_logging_disabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Without debug_logging the handler logs a warning and never touches the coordinator."""
    coordinator = Mock()
    coordinator.async_fire_test_notification = AsyncMock()
    call = _make_call(debug_logging=False, coordinator=coordinator)

    with caplog.at_level(logging.WARNING, logger="custom_components.abode_security"):
        await _fire_test_notification(call)

    coordinator.async_fire_test_notification.assert_not_called()
    assert any(
        "debug_logging" in record.message
        for record in caplog.records
        if record.levelno == logging.WARNING
    )


async def test_errors_when_coordinator_not_ready(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When debug_logging is on but the coordinator hasn't loaded, log an error and bail."""
    call = _make_call(debug_logging=True, coordinator=None)

    with caplog.at_level(logging.ERROR, logger="custom_components.abode_security"):
        await _fire_test_notification(call)

    assert any(
        "coordinator not ready" in record.message
        for record in caplog.records
        if record.levelno == logging.ERROR
    )


async def test_forwards_args_to_coordinator() -> None:
    """Happy path: handler unpacks call.data and calls the coordinator method."""
    coordinator = Mock()
    coordinator.async_fire_test_notification = AsyncMock(return_value=True)
    call = _make_call(
        debug_logging=True,
        coordinator=coordinator,
        data={
            "action_id": "abcd",
            "sensor_entity_id": "binary_sensor.kitchen",
            "mode": "away",
        },
    )

    await _fire_test_notification(call)

    coordinator.async_fire_test_notification.assert_awaited_once_with(
        "abcd", "binary_sensor.kitchen", mode="away"
    )


async def test_logs_when_coordinator_returns_false(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When the coordinator returns False (unknown action / bad mode), surface a warning."""
    coordinator = Mock()
    coordinator.async_fire_test_notification = AsyncMock(return_value=False)
    call = _make_call(debug_logging=True, coordinator=coordinator)

    with caplog.at_level(logging.WARNING, logger="custom_components.abode_security"):
        await _fire_test_notification(call)

    assert any(
        "did not fire" in record.message
        for record in caplog.records
        if record.levelno == logging.WARNING
    )
