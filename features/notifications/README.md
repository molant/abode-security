---
status: pending
feature: notifications
title: Action-Triggered Notifications
phases: 3
---

# Action-Triggered Notifications

> **Progress Tracking**: Update checkboxes in phase files as you complete tasks. Run `/spec-implement features/notifications/phase-1-enrich-event-payload.md` to begin implementation.

## Goal

When an action fires, emit a rich `abode_security.action_triggered` event — including the friendly sensor name, prior/new state, area, and (for co-located motion-cameras) a snapshot served at a `/local/...` URL — so users can wire their own phone notifications via a standard HA automation or the bundled blueprint.

## Concepts

### Action
A user-configured rule that maps one or more triggering binary sensors → one or more alarm switches, scoped to one or more alarm modes (`standby`, `home`, `away`). Defined by the `AbodeAction` dataclass at `custom_components/abode_security/action_manager.py:32`. Already implemented by the dashboard-configuration feature.

### `abode_security.action_triggered` event
The custom HA event the integration fires on the event bus whenever an action's alarms have been processed. Already fired from `action_trigger.py:307`. This spec **adds keys** to its payload (no rename, no removal) so notifications can be built without templating lookups.

### Co-located camera
A `camera.*` entity that lives on the **same HA device** (`device_id`) as the triggering `binary_sensor`. Abode motion-cameras expose both. Some third-party motion-cameras (e.g. Reolink, Wyze) also expose both on one device. A sensor without a co-located camera (window contact, water leak, standalone PIR) simply produces `camera_entity_id: null`. Mapping non-co-located cameras to sensors is **out of scope**.

### Snapshot
A JPEG captured at trigger time via the built-in `camera.snapshot` service, written to `/config/www/abode_security_snapshots/<utc-timestamp-with-ms>_<action_id_first_8_chars>_<sensor_slug>.jpg`, and surfaced on the event as `/local/abode_security_snapshots/<filename>`. The timestamp uses the filename-safe format `YYYYMMDDTHHMMSS_mmm` in UTC. The HA Companion app and most `notify.*` integrations accept this URL form as `data.image`.

### Snapshot retention
Snapshots accumulate on disk. A daily background task deletes JPEGs older than `snapshot_retention_days` (default 30, range 1–365). The retention value is set in the integration's existing options flow.

## Requirements

### Event payload enrichment (Phase 1)
- The existing event keys remain: `action_id`, `action_name`, `triggered_by`, `mode`, `alarms_triggered`, `alarms_failed`, `timestamp`. Existing consumers continue to work.
- New keys (always present; value is `null` when unknown): `sensor_friendly_name`, `sensor_device_class`, `previous_state`, `new_state`, `sensor_area_id`, `sensor_area_name`.
- Sensor state values are captured at the moment of the state-change event and threaded through `_handle_state_change` → `_process_sensor_activation` → `_trigger_action` → `_execute_action`. They are **not** re-fetched at execute time (state may have changed during a configured delay).

### Camera snapshot (Phase 2)
- A camera is "co-located" iff it shares the same `device_id` (via `entity_registry`) as the triggering binary_sensor. When multiple co-located cameras exist, the first one returned by `entity_registry.entries_for_device(...)` (deterministically sorted by `entity_id`) is used. Document this.
- Snapshot capture runs **only when `current_mode in ("home", "away")`**. In `standby`, `camera_entity_id` is still populated when a camera is found (so the user can see the wiring); `snapshot_path` stays `null`.
- Capture is called with `asyncio.wait_for(..., timeout=3.0)`. On timeout or any exception, the event still fires with `snapshot_path: null` and `snapshot_error: "<short reason>"`. On success, `snapshot_error` is `null`.
- New payload keys (always present): `camera_entity_id`, `snapshot_path`, `snapshot_error`.
- File path on disk: `/config/www/abode_security_snapshots/<utc-timestamp-with-ms>_<action_id_first_8_chars>_<sensor_slug>.jpg`. URL form: `/local/abode_security_snapshots/<filename>`.

### Snapshot retention (Phase 3)
- Daily background task registered when the config entry loads, unregistered on unload.
- Deletes files in `/config/www/abode_security_snapshots/` whose mtime is older than `now - timedelta(days=retention)`.
- `snapshot_retention_days` is added to the existing options flow at `config_flow.py:246` (default `30`, range `1–365`).

### Documentation & blueprint (Phase 3)
- New `docs/notifications.md`: event reference table (key, type, when-null), 2–3 copy-pasteable automations, troubleshooting note.
- New `blueprints/abode_security_notification.yaml`: HA blueprint with inputs `notify_target`, optional `action_filter` (action_id), and `critical` (boolean → iOS critical alert + Android channel).
- README addition: a "Notifications" section linking to the new docs page and blueprint.
- `docs/ARCHITECTURE.md` action-trigger flow section (lines 127–145) gets a short paragraph describing the enriched event and snapshot side effect.

### Authorization
- The integration **does not** call `notify.*` services itself. All notification delivery happens in user-owned HA automations / the shipped blueprint. No new admin permissions are introduced.
- Snapshots written under `/config/www/` are reachable at `/local/...` **without authentication** — this is how HA exposes any file in `www/`. The user opted into this trade-off; `docs/notifications.md` must call it out so users with shared HA links understand the surface.

## Phases

| Phase | Title | Description |
|-------|-------|-------------|
| 1 | [Enrich event payload](./phase-1-enrich-event-payload.md) | Thread sensor context through the trigger chain and add 6 new keys to the event payload. No camera work, no breaking change. |
| 2 | [Camera snapshot capture](./phase-2-camera-snapshot.md) | Detect co-located cameras, snapshot under `/config/www/abode_security_snapshots/` with a 3s timeout, expose `/local/...` URL on the event. Mode-gated to `home`/`away`. |
| 3 | [Cleanup, docs, and blueprint](./phase-3-cleanup-docs-blueprint.md) | Daily retention purge + configurable retention in the options flow + `docs/notifications.md` + HA blueprint + README pointer. |

## Related Documentation

- [Phase 1: Enrich event payload](./phase-1-enrich-event-payload.md)
- [Phase 2: Camera snapshot capture](./phase-2-camera-snapshot.md)
- [Phase 3: Cleanup, docs, and blueprint](./phase-3-cleanup-docs-blueprint.md)
- [Architecture overview](../../docs/ARCHITECTURE.md) — see action-trigger flow at lines 127–145
- [Async patterns reference](../../docs/ASYNC_AWAIT_PATTERNS.md)
- Dashboard-configuration spec (related, completed): `features/dashboard-configuration/` — defines `AbodeAction`, the trigger coordinator, and the existing event.

## Testing Tools

> Use these for manual end-to-end verification after automated tests pass. Each phase's "Manual Verification" section names which of these are required for that phase.

| MCP Server | Tool Prefix | Use For |
|-----------|-------------|---------|
| Home Assistant | `mcp__home-assistant__*` | Drive the live HA instance from `./scripts/dev.sh`. Use `mcp__home-assistant__ha_list_resources` to discover available tools/resources in the running session, then `mcp__home-assistant__ha_read_resource` to fetch them. Do **not** assume tool names like `ha_get_state`/`ha_call_event` exist; list resources first. To trigger an `off → on` binary_sensor transition, do not fire an arbitrary event on the bus; either (a) call the mock Abode API's sensor-trip endpoint at `http://localhost:8000/docs`, or (b) use HA's REST API `POST /api/states/<entity_id>` with state `"on"` and valid HA auth. Use the HA MCP for observation (state read, history, log inspection) and verification of the entity/device graph, not for synthesizing the trigger. |

Notes:
- No browser/Playwright MCP is required for this spec — there is no new frontend UI. The dashboard's Action editor is not modified.
- The mock Abode API at `http://localhost:8000/docs` (started by `./scripts/dev.sh`) is the standard fixture for triggering sensor activations in dev. It does **not** expose camera streams — for the Phase 2 manual snapshot test, add a dummy `camera` integration (e.g. the built-in `generic` IP-camera platform pointed at any static image URL) to the dev HA config and assign it to the same device as a mock binary_sensor via the entity registry UI.

## Logging & Diagnostics

> Check these after every test run and build — a zero exit code does not mean clean output.

| Log Source | Location | Format | What to Check |
|-----------|----------|--------|---------------|
| HA Core log (dev) | `docker compose logs homeassistant` (run from project root) | Raw text | Lines containing `custom_components.abode_security.action_trigger` (set the log level for this module to `debug` in the dev `configuration.yaml` while testing). Look for the `_LOGGER.info("Action '%s' executed: ...")` line at `action_trigger.py:309` — confirms the event fired. |
| HA Core log (prod) | `ha core logs` (via the production deploy SSH path documented in `DEPLOY.local.md`) | Raw text | Same module filter. After the Phase 2 change, a `camera.snapshot` failure logs a WARNING — surface it as a known non-fatal pattern. |
| Snapshot directory | `/config/www/abode_security_snapshots/` | JPEG files | Files appear with the documented naming pattern when an action triggers in `home`/`away` with a co-located camera. Stale files (older than retention) disappear after the daily purge. |
| pytest stdout | Terminal during `uv run pytest -m ""` | Plain | Watch for `pytest.PytestUnraisableExceptionWarning` and any "RuntimeWarning: coroutine ... was never awaited" — both have surfaced in this codebase before and the test exit code does not catch them. |

There is no structured JSON log in this project; raw HA logs are the diagnostic surface.

## Access Control

> N/A — this project has no infrastructure access control (no Firestore rules, no Supabase RLS, no IAM policies). Authorization is handled in application code (`@websocket_api.require_admin` on mutation endpoints in `websocket_api.py`). This spec does not add new endpoints, so no new authorization gates are needed.

The integration **does not** call `notify.*` services, so it inherits no notify-related permission concerns.
