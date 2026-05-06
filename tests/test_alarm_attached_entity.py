"""Unit tests for the shared alarm-attached entity base.

These tests construct entities directly without `hass`. They are entered in
the `enabled_tests` allowlist in `tests/conftest.py` so the
pytest-homeassistant-custom-component plugin's auto-injected `hass`
fixturename does not cause them to be skipped.

Regression coverage for issue #8: `AbodeTestModeSwitch.device_info` previously
omitted `sw_version`, drifting from the other two alarm-attached switches.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.abode_security.const import DOMAIN
from custom_components.abode_security.switch import (
    AbodeCMSSettingSwitch,
    AbodeManualAlarmSwitch,
    AbodeTestModeSwitch,
)

ALARM_ID = "area_1"
ALARM_TYPE = "Alarm"
ALARM_NAME = "Abode Alarm"


def _make_alarm() -> MagicMock:
    alarm = MagicMock()
    alarm.id = ALARM_ID
    alarm.type = ALARM_TYPE
    alarm.name = ALARM_NAME
    return alarm


def _make_data() -> MagicMock:
    data = MagicMock()
    data.polling = False
    return data


def _assert_canonical_alarm_device_info(info: DeviceInfo | None, label: str) -> None:
    assert info is not None, f"{label}: device_info missing"
    assert info["identifiers"] == {(DOMAIN, ALARM_ID)}, label
    assert info["manufacturer"] == "Abode", label
    assert info["model"] == ALARM_TYPE, label
    assert info["name"] == ALARM_NAME, label
    assert info["sw_version"] == "1.0.0", (
        f"{label}: device_info must include sw_version (issue #8)"
    )


def test_alarm_attached_device_info_consistent_manual_alarm() -> None:
    """AbodeManualAlarmSwitch.device_info exposes the canonical alarm shape."""
    switch = AbodeManualAlarmSwitch(_make_data(), _make_alarm(), "PANIC")
    _assert_canonical_alarm_device_info(switch.device_info, "manual_alarm")


def test_alarm_attached_device_info_consistent_cms() -> None:
    """AbodeCMSSettingSwitch instances expose the canonical alarm shape."""
    switch = AbodeCMSSettingSwitch(
        _make_data(),
        _make_alarm(),
        name="Monitoring Active",
        icon="mdi:shield-check",
        getter_name="get_monitoring_active",
        setter_name="set_monitoring_active",
    )
    _assert_canonical_alarm_device_info(switch.device_info, "cms_monitoring_active")


def test_alarm_attached_device_info_consistent_test_mode() -> None:
    """AbodeTestModeSwitch.device_info must include sw_version (issue #8 regression)."""
    switch = AbodeTestModeSwitch(_make_data(), _make_alarm())
    _assert_canonical_alarm_device_info(switch.device_info, "test_mode")
