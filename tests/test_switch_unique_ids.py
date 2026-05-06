"""Pure-unit guards on switch entity unique_ids.

These guard the refactor in #7: collapsing the seven CMS-setting subclasses
into a table and folding ``AbodeTestModeSwitch`` onto the same base must not
change any entity's ``unique_id`` (HA's entity_registry would re-register the
entities under fresh ids and silently break user automations).
"""

from __future__ import annotations

from unittest.mock import Mock

from custom_components.abode_security.switch import (
    _CMS_SWITCHES,
    AbodeCMSSettingSwitch,
    AbodeTestModeSwitch,
)

from .test_constants import (
    DISPATCH_FIRE_UID,
    DISPATCH_MEDICAL_UID,
    DISPATCH_POLICE_UID,
    DISPATCH_WITHOUT_VERIFICATION_UID,
    MONITORING_ACTIVE_UID,
    SEND_MEDIA_UID,
    TEST_MODE_UID,
)

CMS_UID_BY_GETTER = {
    "get_monitoring_active": MONITORING_ACTIVE_UID,
    "get_send_media": SEND_MEDIA_UID,
    "get_dispatch_without_verification": DISPATCH_WITHOUT_VERIFICATION_UID,
    "get_dispatch_police": DISPATCH_POLICE_UID,
    "get_dispatch_fire": DISPATCH_FIRE_UID,
    "get_dispatch_medical": DISPATCH_MEDICAL_UID,
}


def _build_alarm() -> Mock:
    alarm = Mock()
    alarm.id = "area_1"
    alarm.name = "Abode Alarm"
    alarm.type = "Alarm"
    return alarm


def _build_data() -> Mock:
    return Mock()


def test_test_mode_switch_unique_id_preserved() -> None:
    switch = AbodeTestModeSwitch(_build_data(), _build_alarm())
    assert switch.unique_id == TEST_MODE_UID


def test_monitoring_active_switch_unique_id_preserved() -> None:
    _assert_cms_unique_id("get_monitoring_active")


def test_send_media_switch_unique_id_preserved() -> None:
    _assert_cms_unique_id("get_send_media")


def test_dispatch_without_verification_switch_unique_id_preserved() -> None:
    _assert_cms_unique_id("get_dispatch_without_verification")


def test_dispatch_police_switch_unique_id_preserved() -> None:
    _assert_cms_unique_id("get_dispatch_police")


def test_dispatch_fire_switch_unique_id_preserved() -> None:
    _assert_cms_unique_id("get_dispatch_fire")


def test_dispatch_medical_switch_unique_id_preserved() -> None:
    _assert_cms_unique_id("get_dispatch_medical")


def test_test_mode_switch_name_and_icon() -> None:
    """Test mode switch keeps its display name + icon after the refactor."""
    switch = AbodeTestModeSwitch(_build_data(), _build_alarm())
    assert switch.name == "Test Mode"
    assert switch.icon == "mdi:test-tube"


def test_test_mode_switch_uses_test_mode_supported_flag() -> None:
    """Test mode switch consults ``test_mode_supported``, not the CMS flag.

    The two attributes are independent on AbodeSystem; mixing them up would
    silently disable the test-mode switch when CMS is unsupported (or vice
    versa).
    """
    switch = AbodeTestModeSwitch(_build_data(), _build_alarm())
    assert switch._support_flag == "test_mode_supported"


def test_cms_setting_base_default_support_flag() -> None:
    base = AbodeCMSSettingSwitch(
        _build_data(),
        _build_alarm(),
        name="Monitoring Active",
        icon="mdi:shield-check",
        getter_name="get_monitoring_active",
        setter_name="set_monitoring_active",
    )
    assert base._support_flag == "cms_settings_supported"


def test_cms_switches_table_covers_all_legacy_entities() -> None:
    """The table must cover every CMS-setting switch the integration shipped."""
    table_getters = {row[2] for row in _CMS_SWITCHES}
    assert table_getters == set(CMS_UID_BY_GETTER)


def _assert_cms_unique_id(getter_name: str) -> None:
    name, icon, getter, setter = _row_for(getter_name)
    switch = AbodeCMSSettingSwitch(
        _build_data(),
        _build_alarm(),
        name=name,
        icon=icon,
        getter_name=getter,
        setter_name=setter,
    )
    assert switch.unique_id == CMS_UID_BY_GETTER[getter_name]


def _row_for(getter_name: str) -> tuple[str, str, str, str]:
    for row in _CMS_SWITCHES:
        if row[2] == getter_name:
            return row
    raise AssertionError(f"No _CMS_SWITCHES row for {getter_name!r}")
