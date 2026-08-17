"""Drive the real manual alarm switch, not a stubbed `switch.turn_on`.

Every existing action-trigger test registers its own fake `switch.turn_on`
service, so `AbodeManualAlarmSwitch.async_turn_on` was never exercised from
the actions path. That gap is why an action wired to the BURGLAR switch could
fail on all ten of its real triggers while the whole suite stayed green.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.abode_security import switch as switch_module
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
    alarm.trigger_manual_alarm = AsyncMock(return_value={"code": 200})
    alarm.find_alarm_event_id = AsyncMock(return_value="tl_1")
    data = MagicMock()
    data.polling = False
    data.abode.dismiss_timeline_event = AsyncMock()
    switch = AbodeManualAlarmSwitch(data, alarm, alarm_type)
    switch.async_write_ha_state = MagicMock()
    switch.schedule_update_ha_state = MagicMock()
    switch.hass = cast(HomeAssistant, _FakeHass())
    return switch, alarm


class _FakeHass:
    """Just enough `hass` for the background event-id lookup.

    `async_create_background_task` has to produce a *real* task so tests can
    await the lookup instead of asserting against a MagicMock that never ran.
    """

    def __init__(self) -> None:
        self.tasks: list[asyncio.Task[Any]] = []

    def async_create_background_task(
        self, target: Any, name: str, eager_start: bool = True
    ) -> asyncio.Task[Any]:
        # Eager, matching HA's default. The hazard is real but narrower than it
        # looks: a task cancelled before it starts never runs its body, and so
        # never its `finally` — but most tests here `gather` the task, so the
        # body runs eventually either way. Measured, exactly one assertion
        # depends on eagerness — `test_retrigger_over_a_deferred_dismissal_is_
        # logged`, where a re-trigger cancels a displaced lookup that must
        # already have entered its body — and it is the only test that fails
        # under a non-eager harness. Keep it anyway: eager start still suspends
        # at the first `await`, so it costs nothing and matches production.
        del name
        task = asyncio.get_running_loop().create_task(target, eager_start=eager_start)
        self.tasks.append(task)
        return task

    async def async_add_executor_job(self, fn: Any, *args: Any) -> Any:
        return fn(*args)


def _tasks(switch: AbodeManualAlarmSwitch) -> list[asyncio.Task[Any]]:
    return cast(_FakeHass, switch.hass).tasks


def _dismiss_mock(switch: AbodeManualAlarmSwitch) -> AsyncMock:
    return cast(AsyncMock, switch._data.abode.dismiss_timeline_event)


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


def _make_api_alarm():
    """A real `Alarm` whose POST succeeds, with no client behind it."""
    from custom_components.abode_security.abode.devices.alarm import Alarm

    # Stateful.__getattr__ resolves through self._state, so that has to exist
    # before any attribute access or the lookup recurses.
    alarm = Alarm({"id": "area_1"}, MagicMock())

    response = MagicMock()
    response.text = AsyncMock(return_value="{}")
    response.json = AsyncMock(return_value={"code": 200})
    alarm._client.send_request = AsyncMock(return_value=response)
    return alarm


async def test_trigger_returns_without_the_timeline_lookup() -> None:
    """The POST is the alarm; the event-id lookup must not be on that path.

    `trigger_manual_alarm` used to poll the timeline inline for up to ~67s
    (`timeline_event_retry_delays` sums to 67) *after* the POST had already
    raised the alarm and notified monitoring. Everything downstream — the
    switch, the actions executor, the `action_triggered` event that drives the
    user's notification — waited that out. See issue #194.
    """
    alarm = _make_api_alarm()
    alarm._find_timeline_alarm_event = AsyncMock(return_value="tl_1")

    result = await alarm.trigger_manual_alarm("PANIC")

    assert result["code"] == 200
    alarm._find_timeline_alarm_event.assert_not_awaited()


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

    `find_alarm_event_id` runs after the alarm is already raised and monitoring
    already contacted, and polls for up to ~67 seconds — so a transient network
    error inside it is entirely plausible. `alarm.py` shadows the builtin
    `Exception` with the Abode one, so the guard inside
    `_find_timeline_alarm_event` does not catch TimeoutError/OSError/ValueError.
    Letting those escape would surface as an unretrieved background-task
    traceback, and back when this ran inline it made the executor record
    `alarms_failed` and fire a critical "no alarm was raised" notification for
    an alarm that was, in fact, raised.
    """
    alarm = _make_api_alarm()
    alarm._find_timeline_alarm_event = AsyncMock(side_effect=boom)

    assert await alarm.find_alarm_event_id() is None


async def test_cancellation_escapes_the_lookup_guard() -> None:
    """The one exception `find_alarm_event_id` must *not* swallow.

    The abandoned-dismissal report hangs off `CancelledError` reaching the
    switch's `finally`. Widening the guard to `except BaseException` would
    silence it with the rest of the suite still green.
    """
    alarm = _make_api_alarm()
    alarm._find_timeline_alarm_event = AsyncMock(side_effect=asyncio.CancelledError)

    with pytest.raises(asyncio.CancelledError):
        await alarm.find_alarm_event_id()


async def test_turn_on_does_not_wait_for_the_event_id() -> None:
    """The whole point of #194: notification latency, not lookup completeness."""
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_1"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)

    await asyncio.wait_for(switch.async_turn_on(), timeout=1)

    assert switch.is_on is True
    assert switch._timeline_id is None

    release.set()
    await asyncio.gather(*_tasks(switch))
    assert switch._timeline_id == "tl_1"


async def test_socketio_event_id_wins_over_the_background_lookup() -> None:
    """`_alarm_event_callback` is the primary source; the poll is the fallback.

    The callback fires on the SocketIO timeline event, which can land while the
    POST is still in flight. Its id is the authoritative one, so a later-landing
    poll result must not overwrite it.
    """
    switch, alarm = _make_switch("PANIC")

    async def _lookup() -> str:
        switch._alarm_event_callback(
            {"is_alarm": "1", "event_code": "1120", "id": "tl_socketio"}
        )
        return "tl_polled"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_lookup)

    await switch.async_turn_on()
    await asyncio.gather(*_tasks(switch))

    assert switch._timeline_id == "tl_socketio"


async def test_background_lookup_does_not_resurrect_an_ended_alarm() -> None:
    """An id landing after the alarm ended is stale — it must not be stored.

    Otherwise the next `turn_off` would dismiss an event that is already gone.
    """
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_1"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)

    await switch.async_turn_on()
    switch._alarm_end_callback({"event_code": "3120"})

    release.set()
    await asyncio.gather(*_tasks(switch), return_exceptions=True)

    assert switch.is_on is False
    assert switch._timeline_id is None


async def test_dismiss_with_a_resolved_event_id_dismisses_inline() -> None:
    """The primary dismissal path: the ID is already known, so just send it."""
    switch, _ = _make_switch("PANIC")

    await switch.async_turn_on()
    await asyncio.gather(*_tasks(switch))
    assert switch._timeline_id == "tl_1"

    await switch.async_turn_off()

    _dismiss_mock(switch).assert_awaited_once_with("tl_1")
    assert switch.is_on is False
    assert switch._timeline_id is None


async def test_lookup_finding_nothing_leaves_no_event_id() -> None:
    """No ID and no dismissal pending: nothing to store, nothing to dismiss."""
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(return_value=None)

    await switch.async_turn_on()
    await asyncio.gather(*_tasks(switch))

    assert switch._timeline_id is None
    assert switch.is_on is True


async def test_a_newer_alarm_is_not_dismissed_by_an_older_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A deferred dismissal must not be spent on an alarm it was not asked about.

    `_timeline_id` is the fallback target when the poll comes back empty, but the
    deferral window is 30-67s wide and a `TimelineGroups.ALARM` event landing
    inside it may be a *new* alarm rather than a late event for ours — the payload
    cannot tell them apart. `dismiss_timeline_event` ignores one specific event,
    so using it here would silently suppress an alarm nobody has seen.

    The deliberate trade: fail to dismiss, loudly, rather than silently swallow a
    live alarm. The new alarm stays visible (`is_on` back to True) and remains
    dismissable via its own id.
    """
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _lookup_that_finds_nothing() -> None:
        await release.wait()
        return None

    alarm.find_alarm_event_id = AsyncMock(side_effect=_lookup_that_finds_nothing)

    await switch.async_turn_on()
    await switch.async_turn_off()

    switch._alarm_event_callback(
        {"is_alarm": "1", "event_code": "1120", "id": "tl_new_alarm"}
    )
    release.set()
    with caplog.at_level(logging.WARNING):
        await asyncio.gather(*_tasks(switch))

    _dismiss_mock(switch).assert_not_awaited()
    assert switch._timeline_id == "tl_new_alarm"
    assert switch.is_on is True
    assert _warnings(caplog) == [
        _unsent_warning(superseded=True, withheld="tl_new_alarm")
    ]


async def test_deferred_dismissal_uses_the_id_the_lookup_found() -> None:
    """The polled id is the one this lookup verifiably found; it wins.

    A stale `_timeline_id` from an earlier alarm must not redirect the dismissal.
    """
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_polled"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)

    await switch.async_turn_on()
    await switch.async_turn_off()
    switch._timeline_id = "tl_stale"

    release.set()
    await asyncio.gather(*_tasks(switch))

    _dismiss_mock(switch).assert_awaited_once_with("tl_polled")
    # A different id was live, so the reconcile leaves it alone.
    assert switch._timeline_id == "tl_stale"


async def test_inline_dismissal_does_not_clobber_a_newer_alarm(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Same reconciliation rule as the deferred path, one round-trip wide.

    `_alarm_event_callback` can fire during the dismissal POST with a new alarm of
    the same type. Its ALARM event will not repeat, so clearing `_timeline_id`
    would make it undismissable — and reporting the switch off would hide it.
    """
    switch, alarm = _make_switch("PANIC")
    await switch.async_turn_on()
    await asyncio.gather(*_tasks(switch))
    assert switch._timeline_id == "tl_1"

    async def _new_alarm_lands_mid_request(_event_id: str) -> None:
        switch._alarm_event_callback(
            {"is_alarm": "1", "event_code": "1120", "id": "tl_newer"}
        )

    _dismiss_mock(switch).side_effect = _new_alarm_lands_mid_request

    with caplog.at_level(logging.INFO):
        await switch.async_turn_off()

    # The original event was dismissed, and the log names *it* rather than the
    # id that happened to be on the instance afterwards.
    _dismiss_mock(switch).assert_awaited_once_with("tl_1")
    assert any(
        record.getMessage() == "Dismissed timeline event: tl_1"
        for record in caplog.records
    )
    # The newer alarm survives, both as an id and as switch state.
    assert switch._timeline_id == "tl_newer"
    assert switch.is_on is True
    assert any("was raised while the previous one" in m for m in _warnings(caplog))


async def test_superseded_still_dismisses_when_the_poll_finds_its_own_event() -> None:
    """`superseded` withdraws the *fallback*, not the dismissal.

    A new alarm arriving after the request disqualifies `_timeline_id` as a
    target, but if the lookup finds the event it was actually looking for, the
    user's dismissal still goes out — and the new alarm is left alone.
    """
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_ours"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)

    await switch.async_turn_on()
    await switch.async_turn_off()
    switch._alarm_event_callback(
        {"is_alarm": "1", "event_code": "1120", "id": "tl_new_alarm"}
    )
    assert switch._lookup is not None and switch._lookup.superseded is True

    release.set()
    await asyncio.gather(*_tasks(switch))

    _dismiss_mock(switch).assert_awaited_once_with("tl_ours")
    assert switch._timeline_id == "tl_new_alarm"
    assert switch.is_on is True


async def test_inline_dismissal_settles_an_earlier_superseded_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Naming the one place an unmet obligation is settled on a judgement.

    Sequence: alarm raised → `turn_off` defers (no id yet) → an ALARM event
    arrives, which marks the lookup `superseded` and revives the switch → the user
    turns off again, dismissing the id now on the entity. That inline dismissal
    settles the earlier request, on the reading that the ALARM event was our own
    alarm's late event — which is the likely one, since deferral only happens when
    no id had arrived.

    It stays quiet deliberately: warning here would fire on the common path and
    devalue the real warnings. The cost, accepted, is that the rarer reading (a
    genuinely different alarm) settles an obligation that was not met. Both
    readings survive because `dismiss_timeline_event` ignores one specific event,
    so the other alarm keeps its own id.
    """
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)

    await switch.async_turn_on()
    await switch.async_turn_off()
    lookup = switch._lookup
    assert lookup is not None and lookup.dismissal_requested

    switch._alarm_event_callback(
        {"is_alarm": "1", "event_code": "1120", "id": "tl_arrived"}
    )
    assert lookup.superseded is True

    with caplog.at_level(logging.WARNING):
        await switch.async_turn_off()
        await asyncio.gather(*_tasks(switch), return_exceptions=True)

    _dismiss_mock(switch).assert_awaited_once_with("tl_arrived")
    assert lookup.dismissal_settled is True
    assert _warnings(caplog) == []


async def test_second_dismiss_after_socketio_revives_the_switch_is_quiet(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A satisfied deferral must not warn that the alarm may still be live.

    Sequence: dismiss inside the lookup window (deferred) → the SocketIO ALARM
    event lands 30-60s later and flips the switch visibly back on → the user
    turns it off again, now with an ID in hand. The inline dismissal succeeds,
    so the deferral is satisfied; warning here would train operators to
    discount the warning that means something.
    """
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)

    await switch.async_turn_on()
    await switch.async_turn_off()
    assert switch._lookup is not None and switch._lookup.dismissal_requested

    switch._alarm_event_callback(
        {"is_alarm": "1", "event_code": "1120", "id": "tl_socketio"}
    )
    assert switch.is_on is True

    with caplog.at_level(logging.WARNING):
        await switch.async_turn_off()

    _dismiss_mock(switch).assert_awaited_once_with("tl_socketio")
    assert switch.is_on is False
    assert not (switch._lookup is not None and switch._lookup.dismissal_requested)
    assert [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ] == []
    await asyncio.gather(*_tasks(switch), return_exceptions=True)


def _dismiss_that_blocks(gate: asyncio.Event) -> Any:
    """A `dismiss_timeline_event` that parks with the request "on the wire"."""

    async def _hang(_event_id: str) -> None:
        gate.set()
        await asyncio.Event().wait()

    return _hang


async def _park_in_flight_dismissal(
    switch: AbodeManualAlarmSwitch, alarm: MagicMock
) -> asyncio.Task[Any]:
    """Get the switch to a deferred dismissal that is mid-request.

    The lookup has to actually suspend for `turn_off` to defer rather than
    dismiss inline — which is the real shape, since Abode needs 30-60s to expose
    the event, and the default `AsyncMock` resolving instantly is the artifact.
    """
    release = asyncio.Event()
    in_flight = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_1"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)
    _dismiss_mock(switch).side_effect = _dismiss_that_blocks(in_flight)

    await switch.async_turn_on()
    await switch.async_turn_off()
    task = _tasks(switch)[-1]
    assert switch._lookup is not None and switch._lookup.dismissal_requested

    release.set()
    await in_flight.wait()
    return task


def _unsent_warning(*, superseded: bool = False, withheld: str | None = None) -> str:
    """The sole abandoned-dismissal warning, rendered."""
    return (
        "The pending dismissal of the PANIC alarm was not sent — the alarm may "
        f"still be live in Abode (superseded={superseded}, withheld id={withheld})"
    )


def _warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ]


async def test_alarm_end_during_an_in_flight_dismissal_is_quiet(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ALARM_END beating our own dismissal response is an ordinary outcome.

    Abode broadcasts the end over SocketIO while processing the very POST we
    are waiting on, so the push routinely wins the race. Warning that the alarm
    "may still be live" immediately after being told it ended is exactly the
    false alarm that devalues the true ones.
    """
    switch, alarm = _make_switch("PANIC")
    task = await _park_in_flight_dismissal(switch, alarm)

    with caplog.at_level(logging.WARNING):
        switch._alarm_end_callback({"event_code": "3120"})
        await asyncio.gather(task, return_exceptions=True)

    assert task.cancelled()
    assert _warnings(caplog) == []


async def test_a_later_cancel_does_not_relabel_an_already_settled_dismissal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the cancel that did the work gets to judge it moot or lost.

    Operator dismisses, Abode reports the alarm ended, operator re-panics. The
    ALARM_END already settled that dismissal as moot; the re-trigger's cancel
    finds no task left and must not relabel it — otherwise the sequence warns
    twice that an alarm Abode just told us ended may still be live.
    """
    switch, alarm = _make_switch("PANIC")
    task = await _park_in_flight_dismissal(switch, alarm)

    with caplog.at_level(logging.WARNING):
        switch._alarm_end_callback({"event_code": "3120"})
        await switch.async_turn_on()
        await asyncio.gather(task, return_exceptions=True)

    assert _warnings(caplog) == []


async def test_settling_one_cycle_does_not_silence_the_next(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Settled-ness belongs to the lookup it settled, not to the entity.

    Cycle 1's dismissal is settled by ALARM_END. Cycle 2 raises a fresh alarm
    whose dismissal is then cancelled out of band — HA stopping its background
    tasks at shutdown, which never reaches `async_will_remove_from_hass`. That one
    really is lost, and any entity-scoped "already settled" state left over from
    cycle 1 would silence it.
    """
    switch, alarm = _make_switch("PANIC")
    first = await _park_in_flight_dismissal(switch, alarm)
    switch._alarm_end_callback({"event_code": "3120"})
    await asyncio.gather(first, return_exceptions=True)

    second = await _park_in_flight_dismissal(switch, alarm)
    assert second is not first

    with caplog.at_level(logging.WARNING):
        second.cancel()
        await asyncio.gather(second, return_exceptions=True)

    assert _warnings(caplog) == [_unsent_warning()]


async def test_out_of_band_cancel_while_armed_is_still_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Shutdown can cancel the task without going through the cancel helper.

    While the dismissal is armed but not yet on the wire, neither
    `_cancel_event_id_lookup` nor the dismissal's own handler would see it —
    the operator would lose the only signal that an alarm may still be live.
    """
    switch, alarm = _make_switch("PANIC")
    polling = asyncio.Event()

    async def _park_polling() -> None:
        polling.set()
        await asyncio.Event().wait()

    alarm.find_alarm_event_id = AsyncMock(side_effect=_park_polling)

    await switch.async_turn_on()
    await switch.async_turn_off()
    assert switch._lookup is not None and switch._lookup.dismissal_requested
    task = _tasks(switch)[0]
    await polling.wait()

    with caplog.at_level(logging.WARNING):
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert _warnings(caplog) == [_unsent_warning()]


async def test_a_displaced_lookup_still_reports_its_own_dismissal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A cancelled lookup owns its obligation all the way to its `finally`.

    A cancelled task runs its `finally` a loop iteration later, and a re-trigger
    plus `turn_off` in that gap installs a *new* lookup. The old one must still
    report the dismissal it was carrying — reading a shared slot would find the
    replacement and report nothing at all — and the new one must be armed.
    """
    switch, alarm = _make_switch("PANIC")
    first = await _park_in_flight_dismissal(switch, alarm)

    # Re-trigger and dismiss with no loop yield in between: `trigger_manual_alarm`
    # is a mock that completes without suspending, so `first` has not unwound.
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)
    await switch.async_turn_on()
    assert not (switch._lookup is not None and switch._lookup.dismissal_requested)
    await switch.async_turn_off()

    second = switch._lookup
    assert second is not None and second.dismissal_requested

    # The displaced lookup's own dismissal was cancelled mid-request, so it is
    # genuinely lost and must be reported — exactly once, by the task that held it.
    with caplog.at_level(logging.WARNING):
        await asyncio.gather(first, return_exceptions=True)

    assert _warnings(caplog) == [_unsent_warning()]
    # ...and cycle 2's obligation is untouched by cycle 1 unwinding.
    assert switch._lookup is second
    assert second.dismissal_requested and not second.dismissal_settled

    switch._cancel_event_id_lookup(settled=True)
    await asyncio.gather(*_tasks(switch), return_exceptions=True)


async def test_teardown_during_an_in_flight_dismissal_still_warns(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The other side of the same coin: here the alarm really is left live."""
    switch, alarm = _make_switch("PANIC")
    await _park_in_flight_dismissal(switch, alarm)

    with caplog.at_level(logging.WARNING):
        await switch.async_will_remove_from_hass()

    # Exactly one: the report lives only in the owning task's `finally`, so a
    # single abandoned dismissal produces a single warning however it was killed.
    assert _warnings(caplog) == [_unsent_warning()]


async def test_second_dismiss_during_an_in_flight_dismissal_does_not_duplicate_it() -> (
    None
):
    """A second `turn_off` must ride the same obligation, not mint a new one.

    The obligation is already outstanding and its request already on the wire.
    Replacing it would strand the original — the earlier shape of this bug —
    and re-sending would POST the same dismissal twice.
    """
    switch, alarm = _make_switch("PANIC")
    task = await _park_in_flight_dismissal(switch, alarm)
    outstanding = switch._lookup

    await switch.async_turn_off()

    assert switch._lookup is outstanding
    assert _dismiss_mock(switch).await_count == 1
    switch._cancel_event_id_lookup(settled=True)
    await asyncio.gather(task, return_exceptions=True)


async def test_retrigger_over_a_deferred_dismissal_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Dropping a dismissal the user asked for cannot be silent."""
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)

    await switch.async_turn_on()
    await switch.async_turn_off()
    assert switch._lookup is not None and switch._lookup.dismissal_requested

    first = _tasks(switch)[0]
    with caplog.at_level(logging.WARNING):
        await switch.async_turn_on()
        # The report comes from the abandoned task's own unwind, not from the
        # re-trigger — that is what makes it exactly-once by construction.
        await asyncio.gather(first, return_exceptions=True)

    assert _warnings(caplog) == [_unsent_warning()]
    # The re-trigger started a second lookup that will never resolve on its own.
    switch._cancel_event_id_lookup(settled=True)
    await asyncio.gather(*_tasks(switch), return_exceptions=True)


async def test_dismiss_inside_the_lookup_window_is_deferred_not_dropped() -> None:
    """Backgrounding the lookup must not break dismissal.

    A dismissal issued inside the resolution window finds `_timeline_id` unset —
    and this is the *common* case, not an edge one: Abode typically needs
    30-60s to expose the event. Blocking `turn_off` until it resolves would
    hold the `PARALLEL_UPDATES = 1` slot and delay the next alarm trigger, so
    the dismissal rides on the lookup instead. What it must never do is what
    the old `if self._timeline_id:` guard did: nothing at all, silently,
    leaving a live alarm in Abode.
    """
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_1"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)

    await switch.async_turn_on()

    # Returns promptly rather than waiting out the lookup.
    await asyncio.wait_for(switch.async_turn_off(), timeout=1)
    assert switch.is_on is False
    _dismiss_mock(switch).assert_not_awaited()

    release.set()
    await asyncio.gather(*_tasks(switch))

    _dismiss_mock(switch).assert_awaited_once_with("tl_1")
    # Spent on the dismissal, not stored for a second one.
    assert switch._timeline_id is None


async def test_deferred_dismissal_failure_is_logged_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The deferred dismissal runs detached, so it has no caller to raise to."""
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> str:
        await release.wait()
        return "tl_1"

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)
    _dismiss_mock(switch).side_effect = AbodeException((500, "boom"))

    await switch.async_turn_on()
    await switch.async_turn_off()

    release.set()
    with caplog.at_level(logging.ERROR):
        await asyncio.gather(*_tasks(switch))

    matches = [
        record
        for record in caplog.records
        if record.levelno >= logging.ERROR
        and "PANIC" in record.getMessage()
        and "Deferred dismissal" in record.getMessage()
    ]
    assert len(matches) == 1, [r.getMessage() for r in caplog.records]


async def test_cancelling_an_in_flight_deferred_dismissal_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A reload landing mid-dismissal leaves the alarm live — say so.

    `except Exception` cannot see this: `CancelledError` is a `BaseException`,
    which is why the report hangs off the task's `finally` rather than a handler.
    """
    switch, alarm = _make_switch("PANIC")
    task = await _park_in_flight_dismissal(switch, alarm)

    with caplog.at_level(logging.WARNING):
        switch._cancel_event_id_lookup()
        await asyncio.gather(task, return_exceptions=True)

    assert task.cancelled()
    assert _warnings(caplog) == [_unsent_warning()]


async def test_deferred_dismissal_warns_when_no_event_id_ever_resolves(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The alarm stays live in Abode — that cannot be silent."""
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _slow_lookup() -> None:
        await release.wait()
        return None

    alarm.find_alarm_event_id = AsyncMock(side_effect=_slow_lookup)

    await switch.async_turn_on()
    await switch.async_turn_off()

    release.set()
    with caplog.at_level(logging.WARNING):
        await asyncio.gather(*_tasks(switch))

    _dismiss_mock(switch).assert_not_awaited()
    matches = [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING
        and "PANIC" in record.getMessage()
        and "was not sent" in record.getMessage()
    ]
    assert len(matches) == 1, [r.getMessage() for r in caplog.records]


async def test_dismiss_without_an_event_id_or_lookup_is_logged_not_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`if self._timeline_id:` used to swallow this outright.

    Reporting the switch off while the alarm is still live in Abode is a
    security path, so the failure has to be visible somewhere. With no lookup
    in flight there is nothing left to defer the dismissal onto.
    """
    switch, _ = _make_switch("PANIC")
    switch._attr_is_on = True

    with caplog.at_level(logging.WARNING):
        await switch.async_turn_off()

    _dismiss_mock(switch).assert_not_awaited()
    assert switch.is_on is False
    matches = [
        record
        for record in caplog.records
        if record.levelno >= logging.WARNING
        and "PANIC" in record.getMessage()
        and "nothing was dismissed" in record.getMessage()
    ]
    assert len(matches) == 1, [r.getMessage() for r in caplog.records]


async def test_alarm_end_event_cancels_the_pending_lookup() -> None:
    """The alarm is over: a deferred dismissal would target a finished event."""
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)

    await switch.async_turn_on()
    await switch.async_turn_off()
    assert switch._lookup is not None and switch._lookup.dismissal_requested

    task = _tasks(switch)[0]
    switch._alarm_end_callback({"event_code": "3120"})

    assert not (switch._lookup is not None and switch._lookup.dismissal_requested)
    await asyncio.gather(task, return_exceptions=True)
    assert task.cancelled()


async def test_failed_retrigger_keeps_the_previous_event_id() -> None:
    """A live alarm must not lose the only ID that can dismiss it.

    `_timeline_id` is cleared before the POST so a SocketIO event landing
    mid-flight wins. When the POST then fails, nothing superseded the alarm
    already being tracked, and its SocketIO ALARM event will not fire twice.
    """
    switch, alarm = _make_switch("PANIC")
    await switch.async_turn_on()
    await asyncio.gather(*_tasks(switch))
    assert switch._timeline_id == "tl_1"

    alarm.trigger_manual_alarm.side_effect = AbodeException((500, "boom"))
    with pytest.raises(AbodeException):
        await switch.async_turn_on()

    assert switch._timeline_id == "tl_1"


async def test_teardown_warns_when_the_lookup_will_not_unwind(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The 5s backstop is not expected to fire, but has to be diagnosable.

    A task that outlives its entity will raise on its next state write against a
    removed one, with nothing connecting the two.
    """
    switch, alarm = _make_switch("PANIC")
    release = asyncio.Event()

    async def _ignores_cancellation() -> None:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.Event().wait()
        await release.wait()

    alarm.find_alarm_event_id = AsyncMock(side_effect=_ignores_cancellation)
    monkeypatch.setattr(switch_module, "EVENT_ID_TASK_TEARDOWN_SECONDS", 0.01)

    await switch.async_turn_on()
    await asyncio.sleep(0)

    with caplog.at_level(logging.WARNING):
        await switch.async_will_remove_from_hass()

    assert any("did not unwind" in message for message in _warnings(caplog))

    release.set()
    await asyncio.gather(*_tasks(switch), return_exceptions=True)


async def test_failed_retrigger_reports_the_lookup_it_could_not_restore(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The ID can be put back; the cancelled lookup cannot.

    A 429 on a re-trigger inside the resolution window leaves the *earlier*
    alarm live with no id and nothing still looking for one. Without this the
    loss is invisible until someone tries to dismiss.
    """
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)

    await switch.async_turn_on()
    assert switch._timeline_id is None

    alarm.trigger_manual_alarm.side_effect = AbodeException((429, "slow down"))
    with caplog.at_level(logging.WARNING), pytest.raises(AbodeException):
        await switch.async_turn_on()

    assert any("no id to dismiss it" in message for message in _warnings(caplog))
    await asyncio.gather(*_tasks(switch), return_exceptions=True)


async def test_a_lookup_that_never_started_is_not_left_behind() -> None:
    """A stranded `_lookup` would promise dismissals nothing can send.

    Defensive: task creation cannot realistically fail on a running loop. But a
    non-None `_lookup` with no task would make `async_turn_off` defer forever and
    `was_resolving` claim a lookup ran.
    """
    switch, _ = _make_switch("PANIC")

    def _fail(target: Any, name: str, eager_start: bool = True) -> Any:
        del name, eager_start
        # Close it, or the unconsumed coroutine surfaces later as an unrelated
        # test's "never awaited" warning.
        target.close()
        raise RuntimeError("no loop")

    hass = cast(_FakeHass, switch.hass)
    hass.async_create_background_task = _fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError):
        await switch.async_turn_on()

    assert switch._lookup is None


async def test_pending_lookup_is_cancelled_on_removal() -> None:
    """A background task outliving its entity is a leak (and a stale write)."""
    switch, alarm = _make_switch("PANIC")
    alarm.find_alarm_event_id = AsyncMock(side_effect=asyncio.Event().wait)

    await switch.async_turn_on()
    task = _tasks(switch)[0]

    await switch.async_will_remove_from_hass()

    assert task.cancelled()


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
