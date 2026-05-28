"""Tests for WebSocket schedule CRUD endpoints."""

from __future__ import annotations

import pytest

from custom_components.abode_security.const import DOMAIN
from custom_components.abode_security.scheduling.clock import HAClock
from custom_components.abode_security.scheduling.manager import ScheduleManager
from custom_components.abode_security.scheduling.mode_changer import HAModeChanger
from custom_components.abode_security.scheduling.scheduler import HAScheduleClock
from custom_components.abode_security.scheduling.store import SchedulesStore
from custom_components.abode_security.websocket_api import (
    async_register_websocket_commands,
)


@pytest.fixture
async def schedule_manager(hass):
    store = SchedulesStore(hass)
    mgr = ScheduleManager(
        hass,
        store,
        HAClock(hass),
        HAScheduleClock(hass),
        HAModeChanger(hass),
    )
    await mgr.async_setup()
    return mgr


@pytest.fixture
async def setup_schedules_ws(hass, schedule_manager):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["schedule_manager"] = schedule_manager
    async_register_websocket_commands(hass)
    return schedule_manager


@pytest.mark.usefixtures("mock_abode", "setup_schedules_ws")
class TestSchedulesWS:
    # --- list ---

    async def test_list_empty(self, hass, hass_ws_client) -> None:
        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/schedules/list"})
        resp = await client.receive_json()

        assert resp["success"]
        assert resp["result"]["schedules"] == []

    async def test_list_sorted_by_created_at(self, hass, hass_ws_client) -> None:
        """Two schedules are returned oldest-first."""
        mgr: ScheduleManager = hass.data[DOMAIN]["schedule_manager"]
        p1 = await mgr.async_create(
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )
        p2 = await mgr.async_create(
            weekdays=["tue"],
            arm_time="08:00",
            disarm_time="17:00",
        )

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/schedules/list"})
        resp = await client.receive_json()

        assert resp["success"]
        ids = [s["id"] for s in resp["result"]["schedules"]]
        assert ids[0] == p1.id
        assert ids[1] == p2.id

    async def test_list_stable_across_calls(self, hass, hass_ws_client) -> None:
        mgr: ScheduleManager = hass.data[DOMAIN]["schedule_manager"]
        await mgr.async_create(weekdays=["mon"], arm_time="22:00", disarm_time="06:00")
        await mgr.async_create(weekdays=["tue"], arm_time="08:00", disarm_time="17:00")

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/schedules/list"})
        r1 = await client.receive_json()
        await client.send_json({"id": 2, "type": "abode_security/schedules/list"})
        r2 = await client.receive_json()

        assert [s["id"] for s in r1["result"]["schedules"]] == [
            s["id"] for s in r2["result"]["schedules"]
        ]

    # --- create ---

    async def test_create_happy_path(self, hass, hass_ws_client) -> None:
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "weekdays": ["mon", "fri"],
                "arm_time": "22:00",
                "disarm_time": "06:00",
            }
        )
        resp = await client.receive_json()
        assert resp["success"]
        pair = resp["result"]
        assert pair["weekdays"] == ["mon", "fri"]
        assert pair["arm_time"] == "22:00"

        # Verify persisted
        await client.send_json({"id": 2, "type": "abode_security/schedules/list"})
        list_resp = await client.receive_json()
        assert len(list_resp["result"]["schedules"]) == 1

    async def test_create_non_admin_unauthorized(
        self, hass, hass_ws_client, hass_read_only_access_token
    ) -> None:
        client = await hass_ws_client(hass, hass_read_only_access_token)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "weekdays": ["mon"],
                "arm_time": "22:00",
                "disarm_time": "06:00",
            }
        )
        resp = await client.receive_json()
        assert not resp["success"]
        assert resp["error"]["code"] == "unauthorized"

    async def test_create_empty_weekdays_validation_error(
        self, hass, hass_ws_client
    ) -> None:
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "weekdays": [],
                "arm_time": "22:00",
                "disarm_time": "06:00",
            }
        )
        resp = await client.receive_json()
        assert not resp["success"]

    async def test_create_arm_equals_disarm_validation_error(
        self, hass, hass_ws_client
    ) -> None:
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/create",
                "weekdays": ["mon"],
                "arm_time": "22:00",
                "disarm_time": "22:00",
            }
        )
        resp = await client.receive_json()
        assert not resp["success"]
        assert resp["error"]["code"] == "validation_error"

    # --- update ---

    async def test_update_partial_name(self, hass, hass_ws_client) -> None:
        """Update only the name; other fields are preserved."""
        mgr: ScheduleManager = hass.data[DOMAIN]["schedule_manager"]
        pair = await mgr.async_create(
            name="Old Name",
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/update",
                "schedule_id": pair.id,
                "name": "New Name",
            }
        )
        resp = await client.receive_json()
        assert resp["success"]
        assert resp["result"]["name"] == "New Name"
        assert resp["result"]["arm_time"] == "22:00"

    async def test_update_only_schedule_id_validation_error(
        self, hass, hass_ws_client
    ) -> None:
        """Update with only schedule_id (no mutable fields) → validation_error."""
        mgr: ScheduleManager = hass.data[DOMAIN]["schedule_manager"]
        pair = await mgr.async_create(
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/update",
                "schedule_id": pair.id,
            }
        )
        resp = await client.receive_json()
        assert not resp["success"]
        assert resp["error"]["code"] == "validation_error"

    async def test_update_unknown_id_not_found(self, hass, hass_ws_client) -> None:
        client = await hass_ws_client(hass)
        await client.send_json(
            {
                "id": 1,
                "type": "abode_security/schedules/update",
                "schedule_id": "nonexistent",
                "name": "X",
            }
        )
        resp = await client.receive_json()
        assert not resp["success"]
        assert resp["error"]["code"] == "not_found"

    # --- delete ---

    async def test_delete_happy_path(self, hass, hass_ws_client) -> None:
        mgr: ScheduleManager = hass.data[DOMAIN]["schedule_manager"]
        pair = await mgr.async_create(
            weekdays=["mon"],
            arm_time="22:00",
            disarm_time="06:00",
        )

        client = await hass_ws_client(hass)
        await client.send_json(
            {"id": 1, "type": "abode_security/schedules/delete", "schedule_id": pair.id}
        )
        resp = await client.receive_json()
        assert resp["success"]
        assert resp["result"]["success"] is True

        # Second delete → not_found
        await client.send_json(
            {"id": 2, "type": "abode_security/schedules/delete", "schedule_id": pair.id}
        )
        resp2 = await client.receive_json()
        assert not resp2["success"]
        assert resp2["error"]["code"] == "not_found"

    # --- not_ready ---

    async def test_list_not_ready(self, hass, hass_ws_client) -> None:
        """list returns not_ready when schedule_manager absent."""
        hass.data[DOMAIN].pop("schedule_manager", None)

        client = await hass_ws_client(hass)
        await client.send_json({"id": 1, "type": "abode_security/schedules/list"})
        resp = await client.receive_json()
        assert not resp["success"]
        assert resp["error"]["code"] == "not_ready"
