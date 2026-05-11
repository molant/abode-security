"""Unit tests for null-safety in alarm_control_panel platform setup."""

from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

from custom_components.abode_security.alarm_control_panel import (
    AbodeAlarm,
    async_setup_entry,
)


async def test_setup_entry_skips_panel_when_no_alarm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """async_setup_entry must skip the panel entity when get_alarm() is None.

    Regression for #70: previously instantiated AbodeAlarm(data, None) and
    crashed when the constructor read attributes off the alarm.
    """
    mock_abode = Mock()
    mock_abode.get_alarm = Mock(return_value=None)

    mock_data = Mock()
    mock_data.abode = mock_abode
    mock_data.polling = False

    mock_entry = Mock()
    mock_entry.runtime_data = mock_data

    added_entities: list[object] = []

    def add_entities(entities: object) -> None:
        added_entities.extend(entities)

    with caplog.at_level(logging.WARNING, logger="custom_components.abode_security"):
        await async_setup_entry(Mock(), mock_entry, add_entities)

    assert not any(isinstance(e, AbodeAlarm) for e in added_entities), (
        "AbodeAlarm was added despite get_alarm() returning None"
    )
    assert any(
        record.levelno == logging.WARNING
        and "no alarm device" in record.message.lower()
        for record in caplog.records
    ), f"Expected WARNING about missing alarm device, got: {caplog.records!r}"


async def test_setup_entry_adds_panel_when_alarm_present() -> None:
    """Happy-path sanity check: AbodeAlarm is registered when get_alarm() returns one."""
    mock_alarm = Mock()
    mock_alarm.id = "alarm-1"
    mock_alarm.type = "Alarm"
    mock_alarm.name = "Abode Alarm"
    mock_alarm.uuid = "alarm-uuid"
    mock_alarm.battery_low = False
    mock_alarm.no_response = False

    mock_events = Mock()
    mock_events.add_connection_status_callback = Mock()
    mock_events.add_device_callback = Mock()
    mock_abode = Mock()
    mock_abode.get_alarm = Mock(return_value=mock_alarm)
    mock_abode.events = mock_events

    mock_data = Mock()
    mock_data.abode = mock_abode
    mock_data.polling = False
    mock_data.entity_ids = set()

    mock_entry = Mock()
    mock_entry.runtime_data = mock_data

    added_entities: list[object] = []

    def add_entities(entities: object) -> None:
        added_entities.extend(entities)

    await async_setup_entry(Mock(), mock_entry, add_entities)

    assert sum(1 for e in added_entities if isinstance(e, AbodeAlarm)) == 1, (
        "Expected exactly one AbodeAlarm panel entity"
    )
