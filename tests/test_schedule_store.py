"""Tests for scheduling/store.py."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from custom_components.abode_security.const import (
    DOMAIN,
    MAX_SCHEDULES,
    REPAIR_ISSUE_CORRUPT_SCHEDULES,
)
from custom_components.abode_security.scheduling.models import ScheduledPair
from custom_components.abode_security.scheduling.store import SchedulesStore

_NOW = datetime(2026, 5, 26, 21, 59, 0, tzinfo=UTC)


def _pair(
    pair_id: str = "test-id", arm: str = "22:00", disarm: str = "06:00"
) -> ScheduledPair:
    return ScheduledPair(
        id=pair_id,
        name="Test",
        weekdays=["mon"],
        arm_time=arm,
        disarm_time=disarm,
        created_at=_NOW,
    )


@pytest.mark.usefixtures("mock_abode")
class TestSchedulesStore:
    async def test_save_and_reload(self, hass) -> None:
        """Save → reload preserves state."""
        store = SchedulesStore(hass)
        await store.async_load()
        pair = _pair()
        await store.async_add(pair)

        store2 = SchedulesStore(hass)
        await store2.async_load()
        result = store2.get("test-id")
        assert result is not None
        assert result.id == "test-id"
        assert result.arm_time == "22:00"

    async def test_whole_file_corruption(self, hass) -> None:
        """Root is a list → empty store + repair issue with count=None."""
        store = SchedulesStore(hass)
        with patch.object(store._store, "async_load", return_value=[1, 2, 3]):
            await store.async_load()

        assert store.get_all() == []

        from homeassistant.helpers import issue_registry as ir

        issues = ir.async_get(hass)
        assert (
            issues.async_get_issue(DOMAIN, REPAIR_ISSUE_CORRUPT_SCHEDULES) is not None
        )

    async def test_per_record_corruption(self, hass) -> None:
        """One bad record in a 3-record file → 2 loaded, repair issue with count=1."""
        good1 = _pair("id-1")
        good2 = _pair("id-2", arm="08:00", disarm="17:00")
        bad = {"id": "id-3", "broken": True}

        fake_data = {
            "schedules": {
                "id-1": good1.to_dict(),
                "id-2": good2.to_dict(),
                "id-3": bad,
            }
        }
        store = SchedulesStore(hass)
        with patch.object(store._store, "async_load", return_value=fake_data):
            await store.async_load()

        assert len(store.get_all()) == 2
        ids = {p.id for p in store.get_all()}
        assert ids == {"id-1", "id-2"}

        from homeassistant.helpers import issue_registry as ir

        issues = ir.async_get(hass)
        issue = issues.async_get_issue(DOMAIN, REPAIR_ISSUE_CORRUPT_SCHEDULES)
        assert issue is not None
        assert issue.translation_placeholders == {"count": "1"}

    async def test_clean_load_clears_issue(self, hass) -> None:
        """A clean load after a corrupt load deletes the repair issue."""
        store = SchedulesStore(hass)
        with patch.object(store._store, "async_load", return_value=[1, 2, 3]):
            await store.async_load()

        from homeassistant.helpers import issue_registry as ir

        issues = ir.async_get(hass)
        assert (
            issues.async_get_issue(DOMAIN, REPAIR_ISSUE_CORRUPT_SCHEDULES) is not None
        )

        store2 = SchedulesStore(hass)
        pair = _pair()
        # Manually set internal state to simulate a prior save with valid data.
        store2._schedules = {pair.id: pair}
        await store2.async_save()

        store3 = SchedulesStore(hass)
        await store3.async_load()
        assert issues.async_get_issue(DOMAIN, REPAIR_ISSUE_CORRUPT_SCHEDULES) is None

    async def test_max_schedules_cap(self, hass) -> None:
        """Adding beyond MAX_SCHEDULES raises ValueError."""
        store = SchedulesStore(hass)
        await store.async_load()

        for i in range(MAX_SCHEDULES):
            arm_h = i % 12
            disarm_h = (arm_h + 1) % 24
            arm_t = f"{arm_h:02d}:00"
            disarm_t = f"{disarm_h:02d}:30"
            if arm_t == disarm_t:
                disarm_t = f"{disarm_h:02d}:45"
            p = _pair(f"id-{i}", arm=arm_t, disarm=disarm_t)
            await store.async_add(p)

        assert len(store.get_all()) == MAX_SCHEDULES

        with pytest.raises(ValueError, match="limit"):
            await store.async_add(_pair("id-overflow", arm="23:00", disarm="23:30"))

    async def test_cap_edge_update_at_capacity_succeeds(self, hass) -> None:
        """Updating an existing record at capacity does not raise."""
        store = SchedulesStore(hass)
        await store.async_load()

        for i in range(MAX_SCHEDULES):
            arm_h = i % 12
            disarm_h = (arm_h + 1) % 24
            arm_t = f"{arm_h:02d}:00"
            disarm_t = f"{disarm_h:02d}:30"
            p = _pair(f"id-{i}", arm=arm_t, disarm=disarm_t)
            await store.async_add(p)

        existing = store.get("id-0")
        assert existing is not None
        updated = ScheduledPair(
            id="id-0",
            name="Updated",
            weekdays=["tue"],
            arm_time=existing.arm_time,
            disarm_time=existing.disarm_time,
            created_at=existing.created_at,
        )
        await store.async_add(updated)  # Should not raise because id already exists
        assert store.get("id-0").name == "Updated"
