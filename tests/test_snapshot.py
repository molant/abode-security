"""Tests for the snapshot module."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security.snapshot import (
    async_capture,
    build_snapshot_path,
    resolve_co_located_camera,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_entity(
    hass: HomeAssistant,
    domain: str,
    platform: str,
    unique_id: str,
    device_id: str | None = None,
) -> er.RegistryEntry:
    """Register an entity, optionally on a device."""
    registry = er.async_get(hass)
    entry = registry.async_get_or_create(domain, platform, unique_id)
    if device_id is not None:
        registry.async_update_entity(entry.entity_id, device_id=device_id)
        entry = registry.async_get(entry.entity_id)  # type: ignore[assignment]
    return entry  # type: ignore[return-value]


def _make_device(hass: HomeAssistant) -> str:
    """Create a mock device and return its device_id."""
    from homeassistant.helpers import device_registry as dr

    config_entry = MockConfigEntry(domain="test_snapshot")
    config_entry.add_to_hass(hass)
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("test_snapshot", "dev1")},
    )
    return device.id


# ---------------------------------------------------------------------------
# resolve_co_located_camera
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mock_abode")
class TestResolveCoLocatedCamera:
    async def test_returns_camera_on_same_device(self, hass: HomeAssistant) -> None:
        device_id = _make_device(hass)
        _register_entity(hass, "binary_sensor", "test_snapshot", "sensor_1", device_id)
        camera_entry = _register_entity(
            hass, "camera", "test_snapshot", "cam_1", device_id
        )
        sensor_entity_id = "binary_sensor.test_snapshot_sensor_1"

        result = resolve_co_located_camera(hass, sensor_entity_id)

        assert result == camera_entry.entity_id

    async def test_picks_first_alphabetically_when_multiple(
        self, hass: HomeAssistant, caplog: pytest.LogCaptureFixture
    ) -> None:
        device_id = _make_device(hass)
        _register_entity(hass, "binary_sensor", "test_snapshot", "sensor_2", device_id)
        cam_b = _register_entity(hass, "camera", "test_snapshot", "b_cam", device_id)
        cam_a = _register_entity(hass, "camera", "test_snapshot", "a_cam", device_id)
        sensor_entity_id = "binary_sensor.test_snapshot_sensor_2"

        with caplog.at_level(logging.DEBUG):
            result = resolve_co_located_camera(hass, sensor_entity_id)

        # The alphabetically-first entity_id wins
        first = min(cam_a.entity_id, cam_b.entity_id)
        assert result == first
        assert any(
            "Multiple co-located cameras" in record.message
            for record in caplog.records
            if record.levelno == logging.DEBUG
        )

    async def test_none_when_sensor_not_in_registry(self, hass: HomeAssistant) -> None:
        result = resolve_co_located_camera(hass, "binary_sensor.never_registered")
        assert result is None

    async def test_none_when_no_device(self, hass: HomeAssistant) -> None:
        # Register sensor without assigning a device
        registry = er.async_get(hass)
        registry.async_get_or_create("binary_sensor", "test_snapshot", "no_device")

        result = resolve_co_located_camera(
            hass, "binary_sensor.test_snapshot_no_device"
        )
        assert result is None

    async def test_none_when_no_camera_on_device(self, hass: HomeAssistant) -> None:
        device_id = _make_device(hass)
        _register_entity(
            hass, "binary_sensor", "test_snapshot", "sensor_only", device_id
        )
        sensor_entity_id = "binary_sensor.test_snapshot_sensor_only"

        result = resolve_co_located_camera(hass, sensor_entity_id)
        assert result is None


# ---------------------------------------------------------------------------
# build_snapshot_path
# ---------------------------------------------------------------------------


class TestBuildSnapshotPath:
    def test_filename_format(self, tmp_path: Path) -> None:
        action_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        sensor_entity_id = "binary_sensor.front_door"
        now = datetime(2024, 6, 15, 12, 34, 56, 789000, tzinfo=UTC)
        www_dir = tmp_path

        fs_path, url = build_snapshot_path(action_id, sensor_entity_id, now, www_dir)

        filename = fs_path.name
        assert re.match(
            r"^\d{8}T\d{6}_\d{3}_aaaaaaaa_binary_sensor_front_door\.jpg$", filename
        ), f"Unexpected filename: {filename}"
        assert fs_path == tmp_path / "abode_security_snapshots" / filename
        assert url == f"/local/abode_security_snapshots/{filename}"

    def test_sensor_slug_replaces_dots(self, tmp_path: Path) -> None:
        action_id = "00000000-0000-0000-0000-000000000000"
        sensor_entity_id = "binary_sensor.motion.extra"
        now = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)

        fs_path, _ = build_snapshot_path(action_id, sensor_entity_id, now, tmp_path)

        assert "binary_sensor_motion_extra" in fs_path.name

    def test_action_id_first_8_chars(self, tmp_path: Path) -> None:
        action_id = "12345678-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        now = datetime(2024, 1, 1, tzinfo=UTC)

        fs_path, _ = build_snapshot_path(action_id, "binary_sensor.x", now, tmp_path)

        assert "12345678" in fs_path.name
        assert "xxxx" not in fs_path.name


# ---------------------------------------------------------------------------
# async_capture
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("mock_abode")
class TestAsyncCapture:
    async def test_success_calls_service_with_correct_args(
        self, hass: HomeAssistant, tmp_path: Path
    ) -> None:
        calls = []

        async def mock_service(call):
            calls.append(call)

        hass.services.async_register("camera", "snapshot", mock_service)
        fs_path = tmp_path / "abode_security_snapshots" / "snap.jpg"

        result = await async_capture(
            hass, camera_entity_id="camera.test", filesystem_path=fs_path
        )

        assert result is None
        assert len(calls) == 1
        assert calls[0].data["entity_id"] == "camera.test"
        assert calls[0].data["filename"] == str(fs_path)

    async def test_creates_parent_directory_if_missing(
        self, hass: HomeAssistant, tmp_path: Path
    ) -> None:
        async def mock_service(_call):
            pass

        hass.services.async_register("camera", "snapshot", mock_service)
        fs_path = tmp_path / "deep" / "nested" / "snap.jpg"

        await async_capture(
            hass, camera_entity_id="camera.test", filesystem_path=fs_path
        )

        assert fs_path.parent.exists()

    async def test_timeout_returns_reason(
        self, hass: HomeAssistant, tmp_path: Path
    ) -> None:
        async def slow_service(_call):
            await asyncio.sleep(5)

        hass.services.async_register("camera", "snapshot", slow_service)
        fs_path = tmp_path / "snap.jpg"

        result = await async_capture(
            hass,
            camera_entity_id="camera.test",
            filesystem_path=fs_path,
            capture_timeout=0.1,
        )

        assert result == "timeout"

    async def test_service_error_returns_truncated_reason(
        self, hass: HomeAssistant, tmp_path: Path
    ) -> None:
        async def error_service(_call):
            raise HomeAssistantError("camera not found")

        hass.services.async_register("camera", "snapshot", error_service)
        fs_path = tmp_path / "snap.jpg"

        result = await async_capture(
            hass, camera_entity_id="camera.test", filesystem_path=fs_path
        )

        assert result is not None
        assert re.match(r"^service_error: camera not found.{0,160}$", result)

    async def test_unexpected_exception_logged_at_exception_level(
        self,
        hass: HomeAssistant,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        async def boom_service(_call):
            raise RuntimeError("boom")

        hass.services.async_register("camera", "snapshot", boom_service)
        fs_path = tmp_path / "snap.jpg"

        with caplog.at_level(logging.ERROR):
            result = await async_capture(
                hass, camera_entity_id="camera.test", filesystem_path=fs_path
            )

        assert result is not None
        assert result.startswith("unexpected: RuntimeError")
        assert any(record.levelno == logging.ERROR for record in caplog.records)

    async def test_os_error_returns_io_error_reason(
        self, hass: HomeAssistant, tmp_path: Path
    ) -> None:
        async def mock_service(_call):
            pass

        hass.services.async_register("camera", "snapshot", mock_service)
        fs_path = tmp_path / "snap.jpg"

        with patch("pathlib.Path.mkdir", side_effect=OSError("permission denied")):
            result = await async_capture(
                hass,
                camera_entity_id="camera.test",
                filesystem_path=fs_path,
            )

        assert result is not None
        assert result.startswith("io_error:")
