---
status: in_progress
phase: 3
feature: notifications
title: Cleanup, docs, and blueprint
---

# Phase 3: Cleanup, docs, and blueprint

Three small deliverables that complete the feature:

1. A daily background task that purges snapshot files older than the configured retention.
2. The retention knob in the existing options flow.
3. The user-facing documentation (`docs/notifications.md`) and a HA blueprint (`blueprints/abode_security_notification.yaml`) for one-click mobile-app notifications, plus a README pointer.

## Context

Phase 2 introduced unbounded disk growth — every motion-camera trigger writes a JPEG to `/config/www/abode_security_snapshots/`. A daily purge keeps the directory bounded, with the retention configurable so power users (or users with cheap storage and forensics needs) can extend it.

The docs and blueprint exist because the integration is intentionally just an event emitter. Without copy-pasteable automation YAML and a blueprint, every user has to re-derive the templating from the event payload reference — a needless papercut.

**Why one blueprint, not three**: the simplest useful blueprint covers the dominant case (single mobile-app notification, optional action filter, optional critical alert). A multi-notifier / area-routing / severity-routing blueprint is a useful follow-up but doubles the surface area and is harder to maintain. Keep it minimal.

**Dependencies**:
- Phase 2 is merged. Snapshots are being written. The event payload contains `snapshot_path`, `snapshot_error`, `camera_entity_id`.

**State of the codebase after Phase 2 (assume this; verify by reading files before editing)**:
- `custom_components/abode_security/snapshot.py` exists with `resolve_co_located_camera`, `build_snapshot_path`, and `async_capture` already implemented and unit-tested. This phase **adds** `async_purge_old` to that same file.
- The event payload has 16 keys: 7 original + 6 from Phase 1 + 3 from Phase 2 (`camera_entity_id`, `snapshot_path`, `snapshot_error`).
- `custom_components/abode_security/strings.json` already contains an `options.step.init` block with entries for `polling_interval`, `enable_events`, `retry_count`, `debug_logging` — extend that same block; do not create a new options step.
- `custom_components/abode_security/config_flow.py:246` defines `AbodeOptionsFlowHandler` with `async_step_init` that already wires four selectors via `vol.Schema`. Add the new selector inside that same schema, after `CONF_RETRY_COUNT` and before `CONF_DEBUG_LOGGING`.
- `custom_components/abode_security/__init__.py` uses a module-level `LOGGER` imported from `.const` (not a local `_LOGGER`). Reuse it.

Read [./README.md](./README.md) for overall feature context, especially the "Snapshot retention" concept.

## Structure

```
custom_components/abode_security/
  const.py                            # modify: add CONF_SNAPSHOT_RETENTION_DAYS, default
  config_flow.py                      # modify: AbodeOptionsFlowHandler — add new field
  snapshot.py                         # modify: add async_purge_old + scheduling helpers
  __init__.py                         # modify: register/unregister daily purge task

tests/
  test_snapshot.py                    # modify: purge unit tests
  test_config_flow.py                 # modify: options flow includes new field
                                      #          (file exists from dashboard-configuration)

docs/
  notifications.md                    # new: user-facing event reference + examples
  ARCHITECTURE.md                     # modify: short note about retention task

blueprints/
  abode_security_notification.yaml    # new: HA blueprint

README.md                             # modify: add "Notifications" section pointing at
                                      #          docs/notifications.md + blueprint
```

If the `blueprints/` directory does not yet exist at the project root, create it. **Discovery result**: `hacs.json` currently does **not** declare `content_in_root` or a `blueprints` key, so HACS will not auto-distribute the blueprint. The README pointer and `docs/notifications.md` must include manual import instructions (Settings → Automations → Blueprints → Import from URL, with `https://raw.githubusercontent.com/molant/abode-security/main/blueprints/abode_security_notification.yaml`). Do not silently assume HACS will pick it up.

## Implementation Checklist

> **Remember**: Update these checkboxes as you complete each task!

### Baseline Test Verification (before starting implementation)

- [ ] Phase 2 is merged and `status: done`.
- [ ] `./scripts/check.sh` exits zero.
- [ ] `uv run pytest -m ""` passes.
- [ ] Confirm `/config/www/abode_security_snapshots/` contains at least one file from Phase 2 manual verification — useful for testing the purge against a real file in dev.

### Sub-Phase A: Snapshot retention purge (logic only, not yet scheduled)

Deployable on its own: a new pure function exists with full test coverage. The daily scheduling happens in Sub-Phase B.

#### Code changes — `snapshot.py`

- [x] Add `async def async_purge_old(snapshot_dir: Path, *, retention_days: int, now: datetime) -> int`:
  - Before creating or scanning the directory, reject unsafe purge roots: if `snapshot_dir.is_absolute()` is false or any path part is `".."`, log a `WARNING` and return `0`. This makes accidental caller bugs fail closed instead of deleting from an unexpected relative path.
  - Lists `snapshot_dir.glob("*.jpg")`.
  - For each, checks `datetime.fromtimestamp(path.stat().st_mtime, tz=UTC) < now - timedelta(days=retention_days)`. If true, `path.unlink()`.
  - On `FileNotFoundError` for an individual file (deleted between glob and unlink — e.g. user manually rm'd it), continue silently.
  - On other `OSError`, log at `WARNING` with the path and continue. Do not raise — a partial purge is better than no purge.
  - Returns the count of files actually deleted (useful for logging).
  - Accepts `now` as a parameter so tests can use a fixed clock.
- [x] Add the `Path.mkdir(parents=True, exist_ok=True)` call on `snapshot_dir` before the glob (so a fresh install without any captures yet doesn't error).

#### Tests — `tests/test_snapshot.py`

- [x] `test_async_purge_old_deletes_files_older_than_retention`: write 5 files to `tmp_path` with `os.utime` setting mtime to 31, 29, 1, 0 days ago and "now". `retention_days=30`. Assert only the 31-day-old file is deleted; assert return value is `1`.
- [x] `test_async_purge_old_returns_zero_when_directory_empty`: assert no error, returns `0`.
- [x] `test_async_purge_old_creates_directory_if_missing`: point at a non-existent path under `tmp_path`; call; assert returns `0` and directory exists.
- [x] `test_async_purge_old_ignores_non_jpg_files`: write `foo.txt` aged 100 days; assert it survives.
- [x] `test_async_purge_old_continues_on_oserror`: monkeypatch `Path.unlink` for one specific file to raise `OSError("permission denied")`. The other stale files must still be deleted; the call must not raise; `caplog` records a WARNING for the failing file.
- [x] `test_async_purge_old_handles_file_disappearing_between_glob_and_unlink`: monkeypatch `Path.unlink` for one file to raise `FileNotFoundError`. Call must not raise. Count of "actually deleted" matches reality.
- [x] `test_async_purge_old_only_touches_snapshot_dir`: create a sibling `tmp_path / "other_dir" / "old.jpg"` with mtime 100 days ago; run the purge against `tmp_path / "snapshots"` only; assert the sibling file still exists. This enforces the "no deletion outside the snapshot directory" constraint from the Constraints section.
- [x] `test_async_purge_old_rejects_relative_or_parent_paths`: call with `Path("abode_security_snapshots")` and with an absolute path containing a `".."` segment; assert both return `0`, log a WARNING, and do not create or delete anything.

### Sub-Phase B: Wire the daily purge into integration setup; add retention to options flow

Deployable on its own: the daily task runs; the options flow exposes the knob; defaults remain at 30 days.

#### Code changes — `const.py`

- [x] Add:
  ```python
  CONF_SNAPSHOT_RETENTION_DAYS = "snapshot_retention_days"
  DEFAULT_SNAPSHOT_RETENTION_DAYS = 30
  ```

#### Code changes — `config_flow.py` (extend `AbodeOptionsFlowHandler.async_step_init`)

- [x] Read the current value from `self.config_entry.options.get(CONF_SNAPSHOT_RETENTION_DAYS, DEFAULT_SNAPSHOT_RETENTION_DAYS)`.
- [x] Add to the `options_schema`:
  ```python
  vol.Optional(
      CONF_SNAPSHOT_RETENTION_DAYS, default=snapshot_retention_days
  ): selector.NumberSelector(
      selector.NumberSelectorConfig(
          min=1, max=365, mode=selector.NumberSelectorMode.BOX
      ),
  ),
  ```
- [x] Field ordering: place after `CONF_RETRY_COUNT` and before `CONF_DEBUG_LOGGING` — groups the snapshot/data-retention knobs separate from logging.
- [x] Add the label/description for this field in `custom_components/abode_security/strings.json` under `options.step.init.data` and `options.step.init.data_description` (the file already exists with entries for `polling_interval`, `enable_events`, `retry_count`, `debug_logging` — add `snapshot_retention_days` alongside them). Use label `"Snapshot Retention (days)"` and description `"How many days to keep camera snapshots in /config/www/abode_security_snapshots/ before the daily purge deletes them."`.

#### Code changes — `__init__.py` (register / unregister the daily task)

- [x] Add module-level imports at the top of `__init__.py` (with the existing imports, not inside `async_setup_entry`):
  ```python
  from datetime import datetime, timedelta
  from homeassistant.helpers.event import async_track_time_interval
  from homeassistant.util import dt as dt_util
  from . import snapshot
  from .const import CONF_SNAPSHOT_RETENTION_DAYS, DEFAULT_SNAPSHOT_RETENTION_DAYS
  ```
- [x] In `async_setup_entry`, after the existing setup, register:
  ```python
  async def _purge_callback(now: datetime) -> None:
      retention = entry.options.get(
          CONF_SNAPSHOT_RETENTION_DAYS, DEFAULT_SNAPSHOT_RETENTION_DAYS
      )
      snapshot_dir = Path(hass.config.path("www/abode_security_snapshots"))
      deleted = await snapshot.async_purge_old(
          snapshot_dir, retention_days=retention, now=now
      )
      if deleted:
          LOGGER.info("Purged %d snapshot(s) older than %d days", deleted, retention)

  unsub_purge = async_track_time_interval(hass, _purge_callback, timedelta(days=1))
  entry.async_on_unload(unsub_purge)
  # Also run once on startup so a long-offline instance doesn't have to wait
  # 24h for the first purge. REQUIRED — not optional.
  hass.async_create_task(_purge_callback(dt_util.utcnow()))
  ```
  (Use the existing `LOGGER` import from `.const`, not a module-local `_LOGGER` — match the current `__init__.py` convention.)
- [x] Note: `async_track_time_interval` fires its first callback after the interval elapses (not immediately). The startup `hass.async_create_task(_purge_callback(...))` line above is **required** so a long-offline instance does not wait 24h for the first purge. Do not omit it.

#### Tests — `tests/test_config_flow.py` (extend the existing options-flow test)

- [x] Add an assertion that the schema returned by `AbodeOptionsFlowHandler.async_step_init` includes a `CONF_SNAPSHOT_RETENTION_DAYS` field with default `30`, min `1`, max `365`.
- [x] Add a test that submitting the form with `snapshot_retention_days=60` persists to `entry.options`.

#### Tests — integration / `__init__.py`

- [x] Add a unit test that advances the HA clock past the daily interval and asserts `snapshot.async_purge_old` was called with the configured retention. Use `mock.patch("custom_components.abode_security.snapshot.async_purge_old")` to intercept. For the clock advance, use `pytest_homeassistant_custom_component.common.async_fire_time_changed` (this project's existing tests under `tests/` already use this helper — grep `async_fire_time_changed` for the canonical import path before adding a new one). Pass `dt_util.utcnow() + timedelta(hours=25)` and `await hass.async_block_till_done()` afterwards. Remember the startup-purge call also invokes `async_purge_old` — assert call_count >= 2, or `reset_mock()` after setup before advancing the clock.
- [x] Add a test that integration unload calls the registered unsub (i.e. no zombie timer after unload). The `entry.async_on_unload` pattern handles this; the test just confirms it.

#### Documentation (End of Sub-Phase B)

- [x] `docs/ARCHITECTURE.md`: append a 1–2 sentence note that the integration registers a daily snapshot purge task with retention controlled by the options flow. Reference `snapshot.py`.

### Sub-Phase C: User-facing docs and blueprint

Deployable on its own: pure docs and YAML. No Python changes.

#### Create `docs/notifications.md`

Required sections (in order):

- [x] **Title + one-paragraph intro** explaining the feature: action triggers fire `abode_security.action_triggered` enriched with sensor context and (when applicable) a snapshot URL; users wire notifications via their own HA automations or the bundled blueprint.

- [x] **Security note** (a callout / `> ⚠️` block):
  > Snapshots are written under `/config/www/` and served at `/local/abode_security_snapshots/...` without authentication. Anyone with the URL can view the image. If your HA instance is internet-exposed or shared, factor this into your retention setting and the URLs you share.

- [x] **Event reference table** with one row per payload key:

  | Key | Type | When `null` | Example |
  |---|---|---|---|
  | `action_id` | str (UUID) | never | `"7f3b…"` |
  | `action_name` | str | never | `"Front Door Motion"` |
  | `triggered_by` | str (entity_id) | never | `"binary_sensor.front_door_motion"` |
  | `mode` | str | never | `"home"`, `"away"`, or `"standby"` |
  | `alarms_triggered` | list[str] | empty list, never null | `["switch.panic_alarm"]` |
  | `alarms_failed` | list[str] | empty list, never null | `[]` |
  | `timestamp` | str (ISO 8601 UTC) | never | `"2026-05-21T18:42:01.234567+00:00"` |
  | `sensor_friendly_name` | str | sensor has no friendly_name attribute | `"Front Door"` |
  | `sensor_device_class` | str | sensor has no device_class | `"motion"`, `"door"`, `"window"` |
  | `previous_state` | str | never (in practice always `"off"` for current trigger logic) | `"off"` |
  | `new_state` | str | never (in practice always `"on"`) | `"on"` |
  | `sensor_area_id` | str | sensor has no assigned area (entity- or device-level) | `"garage"` |
  | `sensor_area_name` | str | same as above | `"Garage"` |
  | `camera_entity_id` | str (entity_id) | no co-located camera on the sensor's device | `"camera.front_door"` |
  | `snapshot_path` | str (URL) | `standby` mode, no co-located camera, OR snapshot failed | `"/local/abode_security_snapshots/20260521T184201_123_7f3b6a2c_binary_sensor_front_door.jpg"` |
  | `snapshot_error` | str | snapshot succeeded or was not attempted | `"timeout"`, `"service_error: ..."` |

- [x] **Minimal automation example** — copy-pasteable YAML for `notify.mobile_app_*`. Use a `choose` action so `data.image` is omitted when `snapshot_path` is `null`; do not send `image: null` in the minimal example because some notify integrations reject it:
  ```yaml
  alias: Abode action notification
  trigger:
    - platform: event
      event_type: abode_security.action_triggered
  action:
    - choose:
        - conditions: "{{ trigger.event.data.snapshot_path is not none }}"
          sequence:
            - service: notify.mobile_app_<your_device>
              data:
                title: "{{ trigger.event.data.action_name }}"
                message: >-
                  {{ trigger.event.data.sensor_friendly_name or trigger.event.data.triggered_by }}
                  {{ 'opened' if trigger.event.data.sensor_device_class in ['door', 'window']
                     else 'detected motion' if trigger.event.data.sensor_device_class == 'motion'
                     else 'triggered' }}
                  ({{ trigger.event.data.mode }})
                data:
                  image: "{{ trigger.event.data.snapshot_path }}"
      default:
        - service: notify.mobile_app_<your_device>
          data:
            title: "{{ trigger.event.data.action_name }}"
            message: >-
              {{ trigger.event.data.sensor_friendly_name or trigger.event.data.triggered_by }}
              {{ 'opened' if trigger.event.data.sensor_device_class in ['door', 'window']
                 else 'detected motion' if trigger.event.data.sensor_device_class == 'motion'
                 else 'triggered' }}
              ({{ trigger.event.data.mode }})
  ```

- [x] **Critical-alert variant** (iOS / Android) — show how to set iOS critical-alert payload fields under `data.push` (including `interruption-level: critical` and a critical `sound` block) and the equivalent `channel: "critical"` on Android.

- [x] **Filtering by action** example — automation that only fires for one specific `action_id`.

- [x] **Troubleshooting** with a checklist:
  - "I'm not getting `snapshot_path` — why?"
    - Is `mode` `standby`? (No snapshot in standby by design.)
    - Does the triggering sensor's HA device also expose a `camera.*` entity? (Check Settings → Devices → the device → Entities.)
    - Is `snapshot_error` populated? (See the `snapshot_error` row above for what each value means.)
    - Is `/config/www/abode_security_snapshots/` writable by the HA process?
  - "The notification arrives but the image doesn't load."
    - Is the URL reachable from the Companion app's network (same LAN, or via remote URL configured in HA)?
    - Has the snapshot already been purged (e.g. retention set to 1 day and the user opens the notification two days later)?
  - "Snapshots are filling my disk."
    - Lower `snapshot_retention_days` in the integration options.

- [x] **Link to the blueprint** at `blueprints/abode_security_notification.yaml` with a one-line "Import this if you just want mobile notifications with snapshots and don't want to write YAML." Because `hacs.json` does not declare blueprint distribution, include manual import instructions using `https://raw.githubusercontent.com/molant/abode-security/main/blueprints/abode_security_notification.yaml`.

#### Create `blueprints/abode_security_notification.yaml`

- [x] HA blueprint with:
  - `domain: automation`
  - `name: "Abode Security — Action notification"`
  - `description`: one paragraph explaining what it does.
  - `source_url: https://github.com/molant/abode-security/blob/main/blueprints/abode_security_notification.yaml`
  - **Inputs**:
    - `notify_target` (required): `selector.text` with `multiline: false` accepting a notify service name (e.g. `notify.mobile_app_iphone`). Document the format in the help text.
    - `action_filter` (optional, default `""`): `selector.text` — when set, the automation only fires for the matching `action_id`. Help text: "Leave blank to notify for **all** triggered actions."
    - `critical` (optional, default `false`): `selector.boolean`. Help text: "iOS critical alerts bypass Do Not Disturb. Requires the HA Companion app permission to be granted. On Android, this sets a high-priority channel."
  - **Trigger**: single event trigger on `abode_security.action_triggered`.
  - **Variables**: assign all blueprint inputs to variables before the condition/action block:
    ```yaml
    variables:
      action_filter: !input action_filter
      critical: !input critical
    ```
  - **Condition**: a template condition that passes when `action_filter | trim == ""` OR `trigger.event.data.action_id == action_filter`.
  - **Action**: use `choose` so the notification call is duplicated for the two data shapes (with image vs without image). Each branch uses `service: !input notify_target` with:
    - `title`: `"{{ trigger.event.data.action_name }}"`
    - `message`: the same templated message as the minimal automation example above
    - `data`:
      - Include `image`: `"{{ trigger.event.data.snapshot_path }}"` only in the branch guarded by `{{ trigger.event.data.snapshot_path is not none }}`.
      - When `critical` is `true`, include nested iOS payload data:
        ```yaml
        push:
          interruption-level: critical
          sound:
            name: default
            critical: 1
            volume: 1.0
        ```
        and Android payload data:
        ```yaml
        channel: "critical"
        priority: high
        ttl: 0
        ```
        HA passes through platform-specific keys safely; unsupported keys are ignored by the target mobile app.

- [x] After creating the file, render it in the HA UI by importing it (Settings → Automations → Blueprints → Import). Confirm the inputs render correctly and the YAML preview validates.

#### Modify `README.md`

- [x] Add a "Notifications" section (after the existing services section, before "Known Limitations" if that section exists):
  ```markdown
  ## Notifications

  When an action triggers, the integration fires `abode_security.action_triggered` with the triggering sensor's friendly name, area, prior/new state, and (when the sensor's device exposes a camera) a snapshot URL. The integration does not send notifications itself — wire your own via an HA automation or import the bundled blueprint.

  See [`docs/notifications.md`](./docs/notifications.md) for the event reference and automation examples, or import the bundled blueprint manually from Settings → Automations → Blueprints → Import from URL:
  `https://raw.githubusercontent.com/molant/abode-security/main/blueprints/abode_security_notification.yaml`
  ```

#### Documentation (End of Sub-Phase C)

- [x] All `docs/` changes are the deliverables of this sub-phase — already done above.
- [x] `CLAUDE.md` — add one short bullet to the project conventions: "User-facing notification docs live at `docs/notifications.md`; the bundled blueprint is at `blueprints/abode_security_notification.yaml`. The integration only fires events — it never calls `notify.*` services."

### Build Verification (required before marking phase complete)

- [ ] `./scripts/check.sh` — exits zero.
- [ ] `uv run pytest -m ""` — full suite passes.
- [ ] Scan pytest stdout for warnings as in prior phases (see [Logging & Diagnostics](./README.md#logging--diagnostics)).
- [ ] Lint the blueprint YAML with the HA blueprint UI (manual) — Settings → Automations → Blueprints → Import → paste the file URL or path, confirm no parse errors.
- [ ] Render `docs/notifications.md` in a Markdown previewer — every code block highlights as YAML/Markdown correctly; every internal link resolves.
- [ ] Mark `status: done` in this file's frontmatter only after all the above pass.

### Manual Verification with MCP Tools

> Use the `mcp__home-assistant__*` tools listed in [Testing Tools](./README.md#testing-tools).

Retention purge:

- [ ] In dev HA, set `snapshot_retention_days` to `1` via Settings → Devices → Abode Security → Configure.
- [ ] Touch a fake old file: `docker compose exec homeassistant touch -d "2 days ago" /config/www/abode_security_snapshots/test_old.jpg`.
- [ ] Touch a fresh file: `docker compose exec homeassistant touch /config/www/abode_security_snapshots/test_new.jpg`.
- [ ] Trigger the purge: simplest path is to advance the dev HA clock by ≥ 24h (or restart the integration so the required startup purge runs). Confirm `test_old.jpg` is gone, `test_new.jpg` remains.
- [ ] Reset `snapshot_retention_days` to `30`.

Blueprint:

- [ ] Import the blueprint via HA UI. Configure it with a real `notify.mobile_app_*` service when available, `action_filter` empty, and `critical: false`. If no mobile notify service is available in dev, use `persistent_notification.create` only to validate the title/message rendering and inspect the automation trace to confirm the `data.image` payload contains the snapshot URL.
- [ ] Trigger an action in `home` mode (with the test camera from Phase 2). Confirm the notification appears with the templated title/message and, for `notify.mobile_app_*`, the image renders from `snapshot_path`.
- [ ] Reconfigure with `action_filter` set to a non-matching `action_id`. Trigger again. Confirm no notification fires.

Docs:

- [ ] Render `docs/notifications.md` in the GitHub preview (after pushing the branch) and confirm formatting is clean.

## Technical Details

### `async_track_time_interval` cadence

The HA helper fires the callback every `interval` after registration. For a 24h interval, the first fire is ~24h after integration setup; the second 48h, etc. There is no "fire at midnight" alignment — purging on a rolling 24h boundary is fine for retention semantics (files survive at least `retention_days * 24h` from their mtime). If a user reloads the integration, the timer resets, but as long as reloads aren't more than daily in practice the purge still runs regularly.

If telemetry later shows users reload constantly and purges never fire, switch to `async_track_time_change` with a fixed hour-of-day. Defer that to a follow-up.

### Why not use `homeassistant.helpers.event.async_track_utc_time_change` directly

`async_track_utc_time_change(hass, callback, hour=3, minute=0, second=0)` would purge at 03:00 UTC daily. It's more deterministic but adds timezone-thinking ("why 03:00? matches what?") with no real benefit for this kind of janitor task. `async_track_time_interval` keeps the intent clear: "run roughly daily."

### Blueprint inputs and the `null` snapshot_path

When `snapshot_path` is `null` (standby, no camera, or capture failure), the Companion app handles `data.image: null` gracefully — it sends the notification without an image. Other notify integrations may not. The blueprint should defensively use `choose` branches so the `data.image:` key is omitted entirely when no snapshot URL exists.

### Discovery: does `hacs.json` declare anything about `blueprints/` for HACS

HACS handles blueprints via the `hacs.json` `content_in_root` and `blueprints` keys. This repo's `hacs.json` currently does not declare a blueprint location for HACS, so users must import the blueprint file from the raw repository URL — note that step in `docs/notifications.md` and the README addition.

## Constraints

- **Retention range**: 1–365 days. Below 1 invites accidental data loss; above 365 invites unbounded growth.
- **Purge is best-effort**: an unlink that errors logs a warning and continues. We do not raise — the integration must never bring down HA over a janitor failure.
- **No deletion of files outside the snapshot directory**: `async_purge_old` only globs within `snapshot_dir` and fails closed for relative paths or paths containing `..` segments. Pass an absolute `Path` from `hass.config.path("www/abode_security_snapshots")` and confirm via tests that unsafe roots are rejected and `snapshot_dir` is the only directory touched.
- **Blueprint is opinionated**: single notify target, optional action filter, optional critical flag. Resist the urge to add more inputs in this spec — a richer blueprint is a separate spec if/when users ask for it.
- **Docs file must compile to GitHub-rendered Markdown** — no proprietary extensions, no draft commenting syntax. Verify by previewing on the branch's GitHub page before merging.
