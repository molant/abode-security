---
status: done
phase: 2
feature: notifications
title: Camera snapshot capture
---

# Phase 2: Camera snapshot capture

When an action triggers in `home` or `away` mode **and** the triggering binary_sensor lives on the same HA device as a `camera.*` entity, capture a JPEG snapshot to `/config/www/abode_security_snapshots/` and surface a `/local/...` URL on the event. Snapshot capture is bounded by a 3-second timeout; on failure the event still fires with `snapshot_path: null` and a populated `snapshot_error` string.

## Context

Phase 1 enriched the event with sensor metadata. This phase adds the one piece a mobile notification really benefits from: an image. The integration owns the snapshot side effect rather than leaving it to the user's automation because:

1. The HA Companion mobile app only attaches **one** image per notification (`data.image: <url>`). If the user's automation called `camera.snapshot` after-the-fact, they'd race the notification — either the image isn't ready when the notification fires, or they'd have to send two notifications.
2. The mapping from "this binary_sensor triggered" → "this camera should snap" is a property of HA's device graph, not the notification automation. It belongs in the integration, where the device-registry lookup is one line.

**Why we limit to `home` / `away`**: the user's stated intent is "when things are triggered" — `standby` is the test/disarmed state and produces noise during configuration. We still populate `camera_entity_id` in `standby` so users can see *why* no snapshot was captured.

**Why a hard 3s timeout**: a slow or unreachable camera must not delay the alarm event. Notification latency for a security event matters more than the snapshot. 3 seconds is the practical upper bound for a healthy IP camera on a LAN; failures past that are real failures and the user's notification should still fire so they can investigate.

**Dependencies / what must be true before starting**:
- Phase 1 is merged. `_SensorTriggerContext` is threaded all the way to `_execute_action`.
- The Phase 1 build verification has passed on the branch.

**State of `action_trigger.py` after Phase 1 (assume this; verify by reading the file before editing)**:
- A frozen dataclass `_SensorTriggerContext` is defined at module top with fields `entity_id`, `friendly_name`, `device_class`, `previous_state`, `new_state`, `area_id`, `area_name` (all immutable).
- `_handle_state_change`, `_process_sensor_activation`, `_trigger_action`, `_delayed_execute`, and `_execute_action` all accept `context: _SensorTriggerContext` instead of `triggered_by: str`.
- `_execute_action` builds an `event_data` dict with 13 keys: the original 7 (`action_id`, `action_name`, `triggered_by`, `mode`, `alarms_triggered`, `alarms_failed`, `timestamp`) plus 6 new (`sensor_friendly_name`, `sensor_device_class`, `previous_state`, `new_state`, `sensor_area_id`, `sensor_area_name`).
- `triggered_by` in the event payload is still a string (`context.entity_id`).

If any of the above is **not** true on the current branch, stop and finish Phase 1 first — do not attempt to compensate from within Phase 2.

Read [./README.md](./README.md) for overall feature context, especially the "Co-located camera" and "Snapshot" concept definitions.

## Structure

```
custom_components/abode_security/
  snapshot.py                    # new: snapshot capture + filename + path helpers
  action_trigger.py              # modify: call snapshot.async_capture from _execute_action,
                                 #         add 3 new keys to event payload

tests/
  test_snapshot.py               # new: unit tests for filename, timeout, mode gate,
                                 #      service-call wiring (mocked)
  test_action_trigger.py         # modify: extend existing tests; assert snapshot keys
  test_actions_integration.py    # modify: integration scenario covering snapshot path
```

## Implementation Checklist

> **Remember**: Update these checkboxes as you complete each task!

### Baseline Test Verification (before starting implementation)

- [x] Confirm Phase 1 is merged and `status: done`.
- [x] `./scripts/check.sh` exits zero.
- [x] `uv run pytest -m ""` passes — including the new Phase 1 tests.

### Sub-Phase A: Snapshot module — pure functions and helpers

Deployable on its own: `snapshot.py` exists, has full unit coverage, but is not yet called from `_execute_action`. No event payload changes. No behavior change observable to users.

#### Create `custom_components/abode_security/snapshot.py`

- [x] Required imports (top of file):
  ```python
  from __future__ import annotations

  import asyncio
  import logging
  from datetime import UTC, datetime
  from pathlib import Path

  from homeassistant.core import HomeAssistant
  from homeassistant.exceptions import HomeAssistantError
  from homeassistant.helpers import entity_registry as er

  _LOGGER = logging.getLogger(__name__)
  ```
- [x] Public functions:
  - `def resolve_co_located_camera(hass: HomeAssistant, sensor_entity_id: str) -> str | None`
    - Look up the sensor's `entity_registry` entry. If it has no `device_id`, return `None`.
    - Call `er.async_entries_for_device(registry, device_id, include_disabled_entities=False)`.
    - Filter to entries whose `entry.domain == "camera"` (preferred over `entity_id.startswith("camera.")` because `RegistryEntry.domain` is the canonical field).
    - If multiple match, sort by `entity_id` (ascending) and return the first. Log at `DEBUG` if multiple matched, naming the one chosen and the ones skipped — important for users debugging "wrong camera snapped."
    - Return `None` if no camera entry is found.
  - `def build_snapshot_path(action_id: str, sensor_entity_id: str, now: datetime, www_dir: Path) -> tuple[Path, str]`
    - Returns `(absolute_filesystem_path, local_url)`.
    - Filename: `<utc-timestamp-with-millis>_<action_id_first_8>_<sensor_slug>.jpg`.
      - Timestamp formatting: `now.astimezone(UTC).strftime("%Y%m%dT%H%M%S_%f")[:-3]` — millisecond precision, no colons (Windows-style fallback even though HA runs on Linux; keeps URLs cleaner).
      - `action_id_first_8`: `action_id[:8]` — UUIDs are 36 chars; the first 8 are unique enough to disambiguate within a single millisecond.
      - `sensor_slug`: replace `.` with `_` in `sensor_entity_id` (e.g. `binary_sensor.front_door` → `binary_sensor_front_door`). Do **not** strip the domain prefix — knowing it was a `binary_sensor.*` is useful when triaging the directory by hand.
    - Filesystem path: `www_dir / "abode_security_snapshots" / filename`.
    - URL: `f"/local/abode_security_snapshots/{filename}"`.
    - The function **does not** take `hass` directly to keep it pure — `www_dir` is supplied by the caller as `Path(hass.config.path("www"))`.
  - `async def async_capture(hass: HomeAssistant, *, camera_entity_id: str, filesystem_path: Path, timeout: float = 3.0) -> str | None`
    - Ensures the parent directory exists (`filesystem_path.parent.mkdir(parents=True, exist_ok=True)`) inside the same `try` block as the service call so filesystem failures return `io_error: ...` instead of aborting the event.
    - Wraps `hass.services.async_call("camera", "snapshot", {"entity_id": camera_entity_id, "filename": str(filesystem_path)}, blocking=True)` in `asyncio.wait_for(..., timeout=timeout)`.
    - Returns `None` on success.
    - Returns a short reason string on failure:
      - `asyncio.TimeoutError` → `"timeout"`
      - `HomeAssistantError as exc` → `f"service_error: {exc}"` (truncated to 200 chars)
      - `OSError as exc` → `f"io_error: {exc}"` (e.g. disk full, permission denied) truncated to 200 chars
      - any other `Exception as exc` → `f"unexpected: {type(exc).__name__}: {exc}"` truncated to 200 chars and logged via `_LOGGER.exception(...)` (records at `ERROR` level with full traceback)
    - On `TimeoutError`, the in-flight task is **not** explicitly cancelled — `asyncio.wait_for` does that automatically. Do not add a manual `task.cancel()` — it has caused double-cancel bugs in this codebase before.

#### Tests — `tests/test_snapshot.py`

- [x] `test_resolve_co_located_camera_returns_camera_on_same_device`: register a `binary_sensor` and a `camera` on the same device via the mock entity_registry; assert returned `entity_id` matches the camera.
- [x] `test_resolve_co_located_camera_picks_first_alphabetically_when_multiple`: register two cameras on the same device (`camera.b_cam`, `camera.a_cam`); assert `camera.a_cam` is returned. Capture `caplog` and assert a `DEBUG` line lists both candidates.
- [x] `test_resolve_co_located_camera_none_when_sensor_not_in_registry`: pass an `entity_id` that was never registered; assert `None`, no exception.
- [x] `test_resolve_co_located_camera_none_when_no_device`: register a sensor with no `device_id`; assert `None`.
- [x] `test_resolve_co_located_camera_none_when_no_camera_on_device`: register only the sensor on a device; assert `None`.
- [x] `test_build_snapshot_path_filename_format`: pass a fixed datetime, action_id `"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"`, sensor `"binary_sensor.front_door"`, and `www_dir=tmp_path`; assert the filename matches `r"^\d{8}T\d{6}_\d{3}_aaaaaaaa_binary_sensor_front_door\.jpg$"`, the filesystem path is `tmp_path / "abode_security_snapshots" / <filename>`, and URL is `"/local/abode_security_snapshots/<that filename>"`.
- [x] `test_async_capture_success_calls_service_with_correct_args`: mock `hass.services.async_call`, assert call args match expected service/data, assert return value is `None`.
- [x] `test_async_capture_creates_parent_directory_if_missing`: point at a path under a fresh `tmp_path`; assert the directory exists after the call.
- [x] `test_async_capture_timeout_returns_reason`: fake the service to `await asyncio.sleep(5)`, set `timeout=0.5`; assert return value is exactly `"timeout"`.
- [x] `test_async_capture_service_error_returns_truncated_reason`: fake the service to raise `HomeAssistantError("camera not found")`; assert return matches `r"^service_error: camera not found.{0,160}$"`.
- [x] `test_async_capture_unexpected_exception_logged_at_exception_level`: fake the service to raise `RuntimeError("boom")`; assert return string starts with `"unexpected: RuntimeError"` and `caplog` captured an `ERROR`-level record with traceback.

### Sub-Phase B: Wire snapshot capture into `_execute_action`

Deployable on its own: the integration now snapshots co-located cameras in `home`/`away` and the event carries three new keys.

#### Code changes — `action_trigger.py`

- [x] Import the new module: `from . import snapshot`.
- [x] In `_execute_action`, **after** the alarm-switch loop completes but **before** `event_data` is built:
  - Resolve the camera: `camera_entity_id = snapshot.resolve_co_located_camera(hass, context.entity_id)`.
  - Initialize: `snapshot_path: str | None = None`, `snapshot_error: str | None = None`.
  - If `camera_entity_id is not None` **and** `current_mode in ("home", "away")`:
    - Build the path: `fs_path, url = snapshot.build_snapshot_path(action.id, context.entity_id, datetime.now(UTC), Path(hass.config.path("www")))`.
    - Capture: `err = await snapshot.async_capture(hass, camera_entity_id=camera_entity_id, filesystem_path=fs_path)`.
    - On success (`err is None`): `snapshot_path = url`.
    - On failure: `snapshot_error = err`. Leave `snapshot_path = None`.
- [x] Extend `event_data` with the three new keys (appended after the Phase 1 additions):
  ```python
  "camera_entity_id": camera_entity_id,
  "snapshot_path": snapshot_path,
  "snapshot_error": snapshot_error,
  ```
- [x] The event still fires unconditionally — capture failures do not abort the event.

#### Tests — extend `tests/test_action_trigger.py`

- [x] `test_event_payload_includes_snapshot_in_home_mode`: configure action with a sensor whose device has a camera entity; trigger in `home` mode; mock `snapshot.async_capture` to succeed; assert `snapshot_path` matches the URL pattern and `snapshot_error is None`.
- [x] `test_event_payload_includes_snapshot_in_away_mode`: same setup as the home-mode test, but with `current_mode == "away"`; assert snapshot capture runs and the event payload matches the home-mode behavior.
- [x] `test_event_payload_no_snapshot_in_standby_mode`: same setup, but `current_mode == "standby"`; assert `camera_entity_id` is the resolved camera (still populated), `snapshot_path is None`, `snapshot_error is None`, and **`snapshot.async_capture` was not called**.
- [x] `test_event_payload_camera_entity_null_when_no_co_located_camera`: sensor with no co-located camera; assert all three new keys are `None`; assert `snapshot.async_capture` was not called.
- [x] `test_event_payload_snapshot_error_on_timeout`: mock `snapshot.async_capture` to return `"timeout"`; assert `snapshot_path is None`, `snapshot_error == "timeout"`, **the event still fires**, and the alarms were still triggered (so `alarms_triggered` matches expectations).
- [x] `test_snapshot_does_not_block_alarms`: mock `async_capture` to `await asyncio.sleep(2.5)` then return `None`; assert the event fires at most ~3s after the trigger, alarms list is populated, and the test does not flake (i.e. wrap with `pytest.mark.timeout(5)` or equivalent).

#### Tests — extend `tests/test_actions_integration.py`

- [x] One integration test that registers a fake camera entity on the same device as the triggering sensor (use HA's `MockEntity`/`MockPlatform` helpers or the existing test scaffolding from `dashboard-configuration` integration tests), patches the `camera.snapshot` service to write a tiny valid JPEG to the configured `.jpg` path, triggers the action in `home` mode, and asserts the listener received an event with `snapshot_path` pointing at the file, the file exists on disk, **and all 16 keys (7 original + 6 Phase 1 + 3 Phase 2) are present** with their expected types — this protects the backwards-compatibility contract for the original 7 keys.

#### Documentation (End of Sub-Phase B)

- [x] `docs/ARCHITECTURE.md` (lines 127–145, after the Phase 1 paragraph): add a short note that triggered actions in `home`/`away` mode capture a snapshot of the triggering sensor's co-located camera (when one exists), saved under `/config/www/abode_security_snapshots/`. One paragraph; do not duplicate the user-facing reference that will land in Phase 3.
- [x] No `README.md` update yet (Phase 3 owns that).
- [x] `CLAUDE.md` — no update needed.

### Build Verification (required before marking phase complete)

- [x] `./scripts/check.sh` — exits zero.
- [x] `uv run pytest -m ""` — full suite passes.
- [x] Scan pytest stdout for unraisable exception warnings and never-awaited-coroutine warnings (see [Logging & Diagnostics](./README.md#logging--diagnostics)).
- [x] Confirm the new `snapshot.py` is exercised at line-coverage parity with the rest of the integration (no untested branches).
- [x] Run `uv run mypy custom_components/abode_security/snapshot.py` and `uv run pyright custom_components/abode_security/snapshot.py` — clean.
- [x] Mark `status: done` in this file's frontmatter only after all the above pass.

### Manual Verification with MCP Tools

> Use the `mcp__home-assistant__*` tools listed in [Testing Tools](./README.md#testing-tools).

Setup (one-time per dev session):

- [ ] In the dev HA UI, add a `generic` IP-camera integration pointed at any reachable JPEG URL (e.g. `https://picsum.photos/640/480.jpg` as `Still Image URL`). Name it "Test Camera".
- [ ] In Settings → Devices → the device hosting the test camera, also assign one of the mock binary_sensors (e.g. `binary_sensor.mock_motion_1`) to **the same device** via the entity registry. (If the mock platform doesn't let you reassign devices, create a small temporary platform in the dev config that registers both entities under one device — pattern is in `dashboard-configuration/phase-4-action-trigger.md` integration tests.)
- [ ] Create an action mapping that binary_sensor to an alarm switch, modes = `[home, away, standby]`.

Verification:

- [ ] Set alarm to `home`. Trigger the sensor. In HA Developer Tools → Events, listen for `abode_security.action_triggered`. Confirm:
  - `camera_entity_id == "camera.test_camera"` (or whatever you named it)
  - `snapshot_path` matches `/local/abode_security_snapshots/<filename>.jpg`
  - `snapshot_error is None`
- [ ] Open the `snapshot_path` URL in a browser (`http://localhost:8123/local/abode_security_snapshots/<filename>`) — the JPEG renders.
- [ ] Set alarm to `standby`. Trigger again. Confirm `camera_entity_id` still populated, `snapshot_path is None`, `snapshot_error is None`. Confirm **no new file** appears under `/config/www/abode_security_snapshots/` for this trigger.
- [ ] Stop the camera integration / break the URL so the snapshot service errors. Trigger in `home` mode. Confirm the event fires with `snapshot_error` populated (`"timeout"` or `"service_error: ..."`), `snapshot_path is None`, and **alarms still triggered** (`alarms_triggered` list is the same as the working case).

## Technical Details

### Why `/config/www/`, not `/config/abode_security_snapshots/`

HA serves any file under `/config/www/` at the `/local/...` URL with no authentication. This is the conventional location for static assets the user wants accessible (it's the only built-in option without a custom view). The HA Companion mobile app's notification image attachment (`data.image`) needs a URL the phone can reach; `/local/...` satisfies that URL requirement, but possession of the exact snapshot URL is enough to fetch the image.

**Trade-off**: anyone with the snapshot URL can view the image without HA login. This is identical to how every HA dashboard background, every `media_player` artwork file, and every Lovelace custom-card asset works today. We surface this in `docs/notifications.md` (Phase 3) so users with publicly shared HA links understand the exposure.

### Why we don't use `Camera.async_get_image()` directly

`camera.async_get_image()` returns bytes — we could save them ourselves and avoid the service-call indirection. But:

1. The `camera.snapshot` service applies any per-camera HA processing (image rotation, motion overlays where supported, format conversions).
2. The service handles `allowlist_external_dirs` correctly. `/config/www/` is allowed by default; we do not have to fiddle with `hass.config.allowlist_external_dirs` from the integration.
3. Mocking a service call in tests is one line. Mocking `Camera.async_get_image()` requires constructing a fake `Camera` instance with the right platform setup — harder.

Stick with the service call.

### Filename character safety

The filename has no user-supplied free-form fields. `entity_id` and `action_id` are both constrained: HA `entity_id` is `[a-z0-9_.]+` and `action_id` is a UUID. The timestamp is fixed-format. So no path-traversal / shell-quoting / NUL-byte concerns. Do **not** add a `pathlib.Path` `.resolve()` + `is_relative_to(www_dir)` check — it would be defensive-against-nothing code and is the kind of thing the codebase has previously rejected (see project memory on "trust internal code").

### Behaviour when `/config/www/` does not exist

A fresh HA install always has `/config/www/`. If the directory is missing, the `mkdir(parents=True, exist_ok=True)` call in `async_capture` will create it. No special-casing needed.

### Why three keys, not a nested object

We could group as `"snapshot": {"camera_entity_id": ..., "path": ..., "error": ...}` — but flat keys are easier to template in HA automations (`{{ trigger.event.data.snapshot_path }}` vs `{{ trigger.event.data.snapshot.path }}`) and keep the payload schema flat overall.

## Constraints

- **Hard timeout**: 3.0 seconds. Not configurable in this phase. If the user later asks for a knob, expose `snapshot_timeout_seconds` in the options flow — but do it as a separate spec; default 3s covers the security-event-latency requirement.
- **Mode gating**: never snapshot in `standby`. Tests must cover this; the docstring must call it out.
- **Event always fires**: snapshot failure never aborts the event. Existing automations and alarm-failure listeners depend on the event firing exactly once per triggered action.
- **No retry**: a snapshot that times out or errors is not retried. Retrying could push the event past 6+ seconds and undermines the latency contract. The user can configure a more reliable camera if it matters.
- **No PII concerns** beyond what `/config/www/` already exposes — the snapshot image is the only new content under that directory, and the user opted into this by configuring a camera on their HA instance.
- **No new external dependencies**: everything in this phase uses HA's built-in `camera.snapshot` service, `entity_registry`, and stdlib (`pathlib`, `asyncio`, `datetime`).
