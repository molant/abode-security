"""Tests for scheduling/manager.py."""

from __future__ import annotations

import asyncio

import pytest

from custom_components.abode_security.const import MAX_SCHEDULES
from custom_components.abode_security.scheduling.clock import HAClock
from custom_components.abode_security.scheduling.manager import ScheduleManager
from custom_components.abode_security.scheduling.mode_changer import HAModeChanger
from custom_components.abode_security.scheduling.scheduler import HAScheduleClock
from custom_components.abode_security.scheduling.store import SchedulesStore


@pytest.fixture
async def manager(hass):
    store = SchedulesStore(hass)
    mgr = ScheduleManager(
        hass,
        store,
        HAClock(hass),
        HAScheduleClock(hass),
        HAModeChanger(hass),
    )
    await mgr.async_setup()
    yield mgr
    await mgr.async_shutdown()


@pytest.mark.usefixtures("mock_abode")
class TestScheduleManagerCRUD:
    async def test_create_returns_pair_with_uuid(self, manager) -> None:
        """Create returns a ScheduledPair with a generated UUID."""
        pair = await manager.async_create(
            weekdays=["mon", "fri"],
            arm_time="22:00",
            disarm_time="06:00",
        )
        assert pair.id
        assert len(pair.id) == 36  # UUID4 string length
        assert pair.weekdays == ["mon", "fri"]
        assert pair.arm_time == "22:00"
        assert pair.disarm_time == "06:00"
        assert pair.enabled is True
        assert pair.name == ""

    async def test_create_with_name(self, manager) -> None:
        pair = await manager.async_create(
            name="Weeknights",
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )
        assert pair.name == "Weeknights"

    async def test_create_validation_failure_not_persisted(self, manager) -> None:
        """Validation failure raises ValueError; nothing is persisted."""
        with pytest.raises(ValueError):
            await manager.async_create(
                weekdays=[],  # empty weekdays
                arm_time="22:00",
                disarm_time="06:00",
            )
        assert await manager.async_get_all() == []

    async def test_create_invalid_arm_equals_disarm(self, manager) -> None:
        with pytest.raises(ValueError, match="differ"):
            await manager.async_create(
                weekdays=["mon"],
                arm_time="08:00",
                disarm_time="08:00",
            )

    async def test_create_invalid_name_too_long(self, manager) -> None:
        with pytest.raises(ValueError, match="100"):
            await manager.async_create(
                name="x" * 101,
                weekdays=["mon"],
                arm_time="22:00",
                disarm_time="06:00",
            )

    async def test_update_valid_partial(self, manager) -> None:
        """Partial update re-validates and persists."""
        pair = await manager.async_create(
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )
        updated = await manager.async_update(pair.id, name="New Name")
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.arm_time == "22:00"

    async def test_update_invalid_raises_and_preserves_state(self, manager) -> None:
        """Invalid update raises ValueError; previous state is preserved."""
        pair = await manager.async_create(
            name="Original",
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )
        with pytest.raises(ValueError):
            await manager.async_update(pair.id, weekdays=[])

        fetched = await manager.async_get(pair.id)
        assert fetched is not None
        assert fetched.name == "Original"
        assert fetched.weekdays == ["mon"]

    async def test_update_unknown_id_returns_none(self, manager) -> None:
        result = await manager.async_update("nonexistent", name="X")
        assert result is None

    async def test_delete_existing_returns_true(self, manager) -> None:
        pair = await manager.async_create(
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )
        result = await manager.async_delete(pair.id)
        assert result is True
        assert await manager.async_get(pair.id) is None

    async def test_delete_unknown_returns_false(self, manager) -> None:
        result = await manager.async_delete("nonexistent")
        assert result is False

    async def test_cap_50th_create_succeeds(self, manager) -> None:
        """Exactly MAX_SCHEDULES creates succeed."""
        for i in range(MAX_SCHEDULES):
            arm_h = i % 12
            disarm_h = (arm_h + 1) % 24
            await manager.async_create(
                weekdays=["mon"],
                arm_time=f"{arm_h:02d}:00",
                disarm_time=f"{disarm_h:02d}:30",
            )
        pairs = await manager.async_get_all()
        assert len(pairs) == MAX_SCHEDULES

    async def test_cap_51st_create_raises(self, manager) -> None:
        """One past MAX_SCHEDULES raises ValueError."""
        for i in range(MAX_SCHEDULES):
            arm_h = i % 12
            disarm_h = (arm_h + 1) % 24
            await manager.async_create(
                weekdays=["mon"],
                arm_time=f"{arm_h:02d}:00",
                disarm_time=f"{disarm_h:02d}:30",
            )
        with pytest.raises(ValueError, match="limit"):
            await manager.async_create(
                weekdays=["mon"],
                arm_time="23:00",
                disarm_time="23:30",
            )

    async def test_two_concurrent_creates_yield_distinct_uuids(self, manager) -> None:
        """Two simultaneous creates produce distinct UUIDs."""
        results = await asyncio.gather(
            manager.async_create(
                weekdays=["mon"],
                arm_time="22:00",
                disarm_time="06:00",
            ),
            manager.async_create(
                weekdays=["tue"],
                arm_time="08:00",
                disarm_time="17:00",
            ),
        )
        ids = {p.id for p in results}
        assert len(ids) == 2


@pytest.mark.usefixtures("mock_abode")
class TestFireFailedRepairIssue:
    """The repair issue must name which half of the schedule failed.

    A failed arm leaves the house unarmed; a failed disarm leaves it armed.
    The event payload has carried `action` since the feature shipped, but the
    repair issue only said "the scheduled arm or disarm", so the notification
    couldn't tell the user which had happened.
    """

    @pytest.mark.parametrize("action", ["arm", "disarm"])
    async def test_issue_records_the_failed_action(self, hass, manager, action) -> None:
        from homeassistant.helpers import issue_registry as ir

        from custom_components.abode_security.const import (
            DOMAIN,
            REPAIR_ISSUE_SCHEDULE_FIRE_FAILED,
        )

        pair = await manager.async_create(
            name="Night arming",
            weekdays=["mon"],
            arm_time="23:00",
            disarm_time="06:00",
        )

        manager._raise_fire_failed_issue(pair, "(600, 'Operation error!')", action)

        issue = ir.async_get(hass).async_get_issue(
            DOMAIN, f"{REPAIR_ISSUE_SCHEDULE_FIRE_FAILED}_{pair.id}"
        )
        assert issue is not None
        placeholders = issue.translation_placeholders or {}
        assert placeholders["action"] == action
        assert placeholders["schedule_name"] == "Night arming"
        assert "Operation error!" in placeholders["error"]
