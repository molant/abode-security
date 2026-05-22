"""Camera snapshot capture for Abode Security action triggers.

Captures JPEG snapshots to /config/www/abode_security_snapshots/ when an
action fires in home/away mode and the triggering sensor has a co-located
camera on the same HA device.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


def resolve_co_located_camera(hass: HomeAssistant, sensor_entity_id: str) -> str | None:
    """Return the entity_id of a camera on the same device as sensor_entity_id.

    Returns the first camera entity (sorted by entity_id) that shares the
    same device_id as the sensor. Returns None when no such camera exists.
    Never snapshots in standby — the caller is responsible for mode-gating.
    """
    registry = er.async_get(hass)
    sensor_entry = registry.async_get(sensor_entity_id)
    if sensor_entry is None or sensor_entry.device_id is None:
        return None

    device_id = sensor_entry.device_id
    device_entries = er.async_entries_for_device(
        registry, device_id, include_disabled_entities=False
    )
    cameras = sorted(
        [e for e in device_entries if e.domain == "camera"],
        key=lambda e: e.entity_id,
    )
    if not cameras:
        return None

    chosen: str = cameras[0].entity_id
    if len(cameras) > 1:
        skipped = [e.entity_id for e in cameras[1:]]
        _LOGGER.debug(
            "Multiple co-located cameras for %s; chose %s, skipped %s",
            sensor_entity_id,
            chosen,
            skipped,
        )
    return chosen


def build_snapshot_path(
    action_id: str,
    sensor_entity_id: str,
    now: datetime,
    www_dir: Path,
) -> tuple[Path, str]:
    """Build the filesystem path and local URL for a snapshot file.

    Returns (absolute_filesystem_path, local_url).

    Filename format: <utc-timestamp-with-millis>_<action_id_first_8>_<sensor_slug>.jpg
    The www_dir argument should be Path(hass.config.path("www")).
    """
    ts = now.astimezone(UTC).strftime("%Y%m%dT%H%M%S_%f")[:-3]
    action_prefix = action_id[:8]
    sensor_slug = sensor_entity_id.replace(".", "_")
    filename = f"{ts}_{action_prefix}_{sensor_slug}.jpg"
    fs_path = www_dir / "abode_security_snapshots" / filename
    url = f"/local/abode_security_snapshots/{filename}"
    return fs_path, url


async def async_capture(
    hass: HomeAssistant,
    *,
    camera_entity_id: str,
    filesystem_path: Path,
    capture_timeout: float = 3.0,
) -> str | None:
    """Capture a camera snapshot to filesystem_path.

    Returns None on success or a short reason string on failure.
    Failures never raise — the caller always fires the event regardless.
    Never snapshot in standby — the caller is responsible for mode-gating.
    """
    try:
        filesystem_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.wait_for(
            hass.services.async_call(
                "camera",
                "snapshot",
                {"entity_id": camera_entity_id, "filename": str(filesystem_path)},
                blocking=True,
            ),
            timeout=capture_timeout,
        )
        return None
    except TimeoutError:
        return "timeout"
    except HomeAssistantError as exc:
        return f"service_error: {exc}"[:200]
    except OSError as exc:
        return f"io_error: {exc}"[:200]
    except Exception as exc:
        reason = f"unexpected: {type(exc).__name__}: {exc}"[:200]
        _LOGGER.exception(
            "Unexpected error capturing snapshot for %s", camera_entity_id
        )
        return reason
