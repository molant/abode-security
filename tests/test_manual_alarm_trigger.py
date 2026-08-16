"""Drive the real manual alarm switch, not a stubbed `switch.turn_on`.

Every existing action-trigger test registers its own fake `switch.turn_on`
service, so `AbodeManualAlarmSwitch.async_turn_on` was never exercised from
the actions path. That gap is why an action wired to the BURGLAR switch could
fail on all ten of its real triggers while the whole suite stayed green.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.abode_security.abode.exceptions import (
    Exception as AbodeException,
)
from custom_components.abode_security.action_trigger import (
    _alarm_outcome,
    _severity,
)
from custom_components.abode_security.const import TRIGGERABLE_ALARM_TYPES
from custom_components.abode_security.switch import (
    MANUAL_ALARM_TYPES,
    AbodeManualAlarmSwitch,
)

UNTRIGGERABLE = sorted(set(MANUAL_ALARM_TYPES) - TRIGGERABLE_ALARM_TYPES)


def _make_switch(alarm_type: str) -> tuple[AbodeManualAlarmSwitch, MagicMock]:
    alarm = MagicMock()
    alarm.id = "area_1"
    alarm.type = "Alarm"
    alarm.name = "Abode Alarm"
    alarm.trigger_manual_alarm = AsyncMock(return_value={"event_id": "tl_1"})
    data = MagicMock()
    data.polling = False
    switch = AbodeManualAlarmSwitch(data, alarm, alarm_type)
    switch.async_write_ha_state = MagicMock()
    return switch, alarm


@pytest.mark.parametrize("alarm_type", sorted(TRIGGERABLE_ALARM_TYPES))
async def test_triggerable_types_reach_the_api(alarm_type: str) -> None:
    switch, alarm = _make_switch(alarm_type)

    await switch.async_turn_on()

    alarm.trigger_manual_alarm.assert_awaited_once_with(alarm_type)
    assert switch.is_on is True


@pytest.mark.parametrize("alarm_type", UNTRIGGERABLE)
async def test_untriggerable_types_are_refused_before_any_request(
    alarm_type: str,
) -> None:
    """No request is made at all — the API would just 400.

    Regression test for the incident: `switch.abode_alarm_burglar_alarm` was a
    selectable, apparently-normal switch that could never raise an alarm.
    """
    switch, alarm = _make_switch(alarm_type)

    with pytest.raises(ServiceValidationError):
        await switch.async_turn_on()

    alarm.trigger_manual_alarm.assert_not_awaited()
    assert switch.is_on is False


async def test_api_rejection_propagates_rather_than_being_swallowed() -> None:
    """The caller must be able to tell a raised alarm from a failed one.

    `async_turn_on` used to be wrapped in @handle_abode_errors. That decorator
    never actually caught anything the client raises, but had it worked it
    would have turned this into a silent success.
    """
    switch, alarm = _make_switch("PANIC")
    alarm.trigger_manual_alarm.side_effect = AbodeException(
        (400, '{"errorCode":16013,"message":"invalid {{param}} value."}')
    )

    with pytest.raises(AbodeException):
        await switch.async_turn_on()

    assert switch.is_on is False


async def test_repeat_trigger_is_not_suppressed() -> None:
    """A second trigger must still hit the API.

    `async_turn_on` used to early-return whenever `_attr_is_on` was already
    set, and that flag is only cleared by an ALARM_END timeline event. A
    missed event stranded the switch `on` and silently no-opped every later
    action — while the executor recorded it as a successful arm.
    """
    switch, alarm = _make_switch("PANIC")

    await switch.async_turn_on()
    await switch.async_turn_on()

    assert alarm.trigger_manual_alarm.await_count == 2


@pytest.mark.parametrize(
    "boom",
    [
        TimeoutError("timed out"),
        OSError("connection reset"),
        ValueError("bad event_utc"),
    ],
)
async def test_timeline_lookup_failure_cannot_undo_a_raised_alarm(boom) -> None:
    """A raised alarm must never be reported as a failure.

    `trigger_manual_alarm` POSTs, confirms code 200 — at which point the alarm
    IS raised and monitoring HAS been contacted — and only then polls the
    timeline for an event id, for up to ~67 seconds. `alarm.py` shadows the
    builtin `Exception` with the Abode one, so the guard inside
    `_find_timeline_alarm_event` does not catch TimeoutError/OSError/ValueError.
    Letting those escape would make the executor record `alarms_failed` and
    fire a critical "no alarm was raised" notification for an alarm that was,
    in fact, raised.
    """
    from custom_components.abode_security.abode.devices.alarm import Alarm

    # Stateful.__getattr__ resolves through self._state, so that has to exist
    # before any attribute access or the lookup recurses.
    alarm = Alarm({"id": "area_1"}, MagicMock())

    response = MagicMock()
    response.text = AsyncMock(return_value="{}")
    response.json = AsyncMock(return_value={"code": 200})
    alarm._client.send_request = AsyncMock(return_value=response)
    alarm._find_timeline_alarm_event = AsyncMock(side_effect=boom)

    result = await alarm.trigger_manual_alarm("PANIC")

    assert result["code"] == 200
    assert result.get("event_id") is None


@pytest.mark.parametrize(
    ("triggered", "failed", "expected"),
    [
        (["a"], [], "armed"),
        (["a"], ["b"], "partial"),
        ([], ["b"], "failed"),
        ([], [], "none"),
    ],
)
def test_alarm_outcome(triggered, failed, expected) -> None:
    assert _alarm_outcome(triggered, failed) == expected


@pytest.mark.parametrize(
    ("triggered", "failed", "mode", "expected"),
    [
        (["a"], [], "away", "critical"),
        (["a"], [], "home", "critical"),
        # A promised alarm that did NOT fire is the most urgent case, not the
        # least — the user believes monitoring was contacted.
        ([], ["b"], "standby", "critical"),
        ([], [], "away", "high"),
        ([], [], "home", "normal"),
        ([], [], "standby", "normal"),
    ],
)
def test_severity(triggered, failed, mode, expected) -> None:
    assert _severity(triggered, failed, mode) == expected
