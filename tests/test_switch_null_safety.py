"""Unit tests for null-safety in switch platform setup."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.abode_security.switch import (
    _CMS_SWITCHES,
    MANUAL_ALARM_TYPES,
    AbodeCMSSettingSwitch,
    AbodeManualAlarmSwitch,
    AbodeTestModeSwitch,
    async_setup_entry,
)


async def test_setup_entry_skips_alarm_attached_when_no_alarm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """async_setup_entry must skip alarm-attached switches when get_alarm() is None.

    Regression for #70: previously crashed with TypeError as the alarm-attached
    switch constructors received `None` where `Alarm` was required. Reachable
    on transient pre-load state or accounts without an alarm device.
    """
    mock_abode = Mock()
    mock_abode.get_devices = AsyncMock(return_value=[])
    mock_abode.get_automations = AsyncMock(return_value=[])
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

    assert not any(isinstance(e, AbodeManualAlarmSwitch) for e in added_entities), (
        "AbodeManualAlarmSwitch was added despite get_alarm() returning None"
    )
    assert not any(isinstance(e, AbodeCMSSettingSwitch) for e in added_entities), (
        "AbodeCMSSettingSwitch was added despite get_alarm() returning None"
    )
    assert not any(isinstance(e, AbodeTestModeSwitch) for e in added_entities), (
        "AbodeTestModeSwitch was added despite get_alarm() returning None"
    )
    # The warning is the only operator-visible signal that alarm-attached
    # entities were silently skipped; assert it so a future refactor that
    # downgrades the log level fails this test rather than silently degrading.
    assert any(
        record.levelno == logging.WARNING
        and "no alarm device" in record.message.lower()
        for record in caplog.records
    ), f"Expected WARNING about missing alarm device, got: {caplog.records!r}"


async def test_setup_entry_adds_alarm_attached_when_alarm_present() -> None:
    """async_setup_entry must still add all alarm-attached switches when alarm is present.

    Sanity check that the null-guard doesn't break the happy path. Expected
    counts: 7 manual-alarm switches (one per MANUAL_ALARM_TYPES entry),
    6 CMS settings switches (one per _CMS_SWITCHES row), 1 test-mode switch.
    """
    mock_alarm = Mock()
    mock_alarm.id = "alarm-1"
    mock_alarm.type = "Alarm"
    mock_alarm.name = "Abode Alarm"

    mock_abode = Mock()
    mock_abode.get_devices = AsyncMock(return_value=[])
    mock_abode.get_automations = AsyncMock(return_value=[])
    mock_abode.get_alarm = Mock(return_value=mock_alarm)

    mock_data = Mock()
    mock_data.abode = mock_abode
    mock_data.polling = False

    mock_entry = Mock()
    mock_entry.runtime_data = mock_data

    added_entities: list[object] = []

    def add_entities(entities: object) -> None:
        added_entities.extend(entities)

    await async_setup_entry(Mock(), mock_entry, add_entities)

    manual_alarm_count = sum(
        1 for e in added_entities if isinstance(e, AbodeManualAlarmSwitch)
    )
    cms_setting_count = sum(
        1
        for e in added_entities
        if isinstance(e, AbodeCMSSettingSwitch)
        and not isinstance(e, AbodeTestModeSwitch)
    )
    test_mode_count = sum(
        1 for e in added_entities if isinstance(e, AbodeTestModeSwitch)
    )

    assert manual_alarm_count == len(MANUAL_ALARM_TYPES), (
        f"Expected {len(MANUAL_ALARM_TYPES)} manual-alarm switches, "
        f"got {manual_alarm_count}"
    )
    assert cms_setting_count == len(_CMS_SWITCHES), (
        f"Expected {len(_CMS_SWITCHES)} CMS-setting switches, got {cms_setting_count}"
    )
    assert test_mode_count == 1, f"Expected 1 test-mode switch, got {test_mode_count}"
