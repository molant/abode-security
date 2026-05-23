---
status: pending
phase: 4
feature: notifications
title: Cameras tab + notification deep-link
---

# Phase 4: Cameras tab + notification deep-link

Add a "Cameras" tab to the existing Abode Security custom panel that lists every camera entity sharing a device with an Abode-managed entity, and update the notification blueprint/docs so tapping a snapshot notification deep-links to that tab scrolled/highlighted on the triggering camera.

## Context

Phases 1–3 deliver the event, the snapshot, and the docs/blueprint. The current blueprint (commit on `feat/notifications`) sets `url`/`clickAction` to `entityId:<camera_entity_id>`, which **does not work on iOS Companion** (treats `entityId:` as an unknown URL scheme and surfaces a confirmation prompt) and is unreliable on Android in mixed-dashboard setups. A path-based fallback like `/lovelace/0?more_info=<entity_id>` also fails on iOS Companion — observed live: it navigates to the dashboard but ignores the `more_info` query string.

The only stable destination across iOS/Android Companion versions and user dashboard layouts is a URL the integration **owns end-to-end**. The custom panel at `/abode_security` (note: underscore — the panel registers with `frontend_url_path="abode_security"` at `__init__.py:268`, despite the directory name using hyphens elsewhere) is already registered for every install, so adding a Cameras tab to it makes the destination predictable: for every user who installs the integration, the same URL works.

**Why "shares a device with an Abode entity"** is the discovery rule (rather than "entities with `platform == abode_security`"):
- Abode motion-cameras: the integration registers both `binary_sensor` and `camera` on the same device — they match.
- Third-party motion-cameras (e.g. Reolink, Wyze) paired with an Abode contact sensor on the same physical door, where the user manually grouped them under one HA device for the snapshot path to work — they match too.
- A `camera.*` entity unrelated to any Abode sensor — does not match. Surfacing it here would muddy the UX.

Note: this rule is **stricter** than `snapshot.resolve_co_located_camera` in `snapshot.py:22-54`. The snapshot resolver just looks at the triggering sensor's device for any co-located camera — it does not require the sensor itself to be an Abode entity. That's intentionally looser so a user can manually group a third-party motion sensor with a camera and still get snapshots. The tab applies the stricter "device must have at least one Abode entity" rule because surfacing every camera in HA that happens to share a device with anything would dilute the panel's purpose. Do **not** unify the two rules in this phase.

**Auto-discovery requirement (user instruction):** the tab must be created automatically for everyone installing the integration, and newly-added cameras must appear without restarting HA. The first is free (the panel is already registered at config-entry-setup time, and adding a tab to its template is purely a frontend change). The second is satisfied by refetching the camera list when the tab activates — HA's WebSocket event subscription for `entity_registry_updated` is also acceptable and slightly nicer, but a tab-activation refetch is cheap and avoids long-lived subscriptions.

**Why a still-image MVP, not live stream:**
- The notification's payload already includes the snapshot URL (`/local/abode_security_snapshots/<file>.jpg`), which the Companion app shows on long-press. The Cameras tab's job is to show the *current* state when the user investigates after the fact.
- A `<img src="/api/camera_proxy/<entity_id>?token=<signed>">` refresh-every-5s pattern is ~15 lines of code with no streaming dependencies. It satisfies the "see what's happening now" need for ~95% of users.
- True live stream (HLS via `<ha-camera-stream>` or WebRTC) is meaningful gravy, but bumps the implementation cost ~3× (auth tokens, stream URL fetch, error handling, fullscreen overlay). Defer to a follow-up phase.

**Dependencies / what must be true before starting**:
- Phases 1–3 are merged. The event already carries `camera_entity_id` and `snapshot_path`.
- The `feat/notifications` branch is at the post-Phase-3 commit that adds `url`/`clickAction` with `entityId:` values. This phase replaces those values.

Read [./README.md](./README.md) for overall feature context.

## Structure

```
custom_components/abode_security/
  websocket_api.py               # modify: add `abode_security/entities/cameras` endpoint

frontend/src/
  cameras-tab.ts                 # new: tab component (~150 LOC)
  abode-panel.ts                 # modify: register the third tab + parse ?tab/?camera
  api.ts                         # modify: fetchCameras helper + AbodeCamera type
  types.ts                       # modify: export AbodeCamera

frontend/src/__tests__/
  cameras-tab.test.ts            # new: render + deep-link + refresh
  test-helpers.ts                # modify: default mock for new WS endpoint
  abode-panel.test.ts            # modify (if it exists): assert tab switch by query param

custom_components/abode_security/www/
  abode-security-panel.js        # REBUILD via `npm --prefix frontend run build`

tests/
  test_websocket_api.py          # modify: cameras endpoint tests

blueprints/
  abode_security_notification.yaml  # modify: replace entityId: with /abode_security?…

docs/
  notifications.md               # modify: update example automation + new tab section
  ARCHITECTURE.md                # modify: one-paragraph note on the new tab
```

## Implementation Checklist

> **Remember**: Update these checkboxes as you complete each task!

### Baseline Test Verification (before starting implementation)

- [ ] Confirm Phases 1–3 are merged and `status: done`.
- [ ] `./scripts/check.sh` exits zero.
- [ ] `npm --prefix frontend run test` passes.
- [ ] `grep -c "abode-cameras-tab" custom_components/abode_security/www/abode-security-panel.js` returns `0` — confirms the bundle is in its pre-Phase-4 state (no Cameras tab yet). This is a sanity check that the working tree's bundle matches what's deployed; if it returns ≥1 already, someone deployed a partial change and you need to reconcile before starting.
- [ ] `grep -E "entityId:" blueprints/abode_security_notification.yaml` returns the two pre-fix matches in the snapshot branches — sanity check that the blueprint is in its pre-Phase-4 state and you're about to replace what you expect.

### Sub-Phase A: Backend — `abode_security/entities/cameras` WS endpoint

Deployable on its own: the endpoint exists and is admin-gated; no frontend caller yet. Tests cover the discovery rule end-to-end against a mock entity/device registry.

#### Code changes — `custom_components/abode_security/websocket_api.py`

- [ ] Add a new `@websocket_command` handler `websocket_entities_cameras` with the same `@require_admin + @async_response` decorators that `websocket_entities_sensors` (`websocket_api.py:545-619`) uses. WS type: `"abode_security/entities/cameras"`.
- [ ] **Register the handler.** Add a call to `websocket_api.async_register_command(hass, websocket_entities_cameras)` inside `async_register_websocket_commands` next to the existing `websocket_entities_alarms` registration. Without this line the handler is defined but never wired into HA's WS dispatcher — `callWS({type: "abode_security/entities/cameras"})` returns `unknown_command` and Sub-Phase B silently fails against a live HA.
- [ ] Discovery rule — **deviate from `entities/sensors` here** by iterating the entity registry rather than `hass.states.async_all(...)`. Reason: iterating the registry lets us deterministically filter on `hidden_by` / `disabled_by` rather than relying on `async_all` already-skipping disabled entities, and means a newly re-enabled camera appears on the next tab-activation refetch without an HA restart. Steps:
  1. Resolve the abode_security config entry: `abode_entry = next(e for e in hass.config_entries.async_entries(DOMAIN))`. (The integration is `single_config_entry: true` per the existing manifest, so exactly one entry exists when this handler is reachable.) The remaining steps use `abode_entry.entry_id` to compare against `entry.config_entry_id` on entity-registry entries; the loop-local variable is `entry` (an entity-registry entry, not the config entry — distinct names avoid shadowing).
  2. Build the set of "Abode device IDs": iterate the entity registry once, collecting `entry.device_id` for every entity registry entry whose `config_entry_id == abode_entry.entry_id` and `device_id is not None`.
  3. Iterate the entity registry again, yielding entries where `entry.domain == "camera"` AND `entry.device_id` is in that set AND `entry.hidden_by is None` AND `entry.disabled_by is None`.
- [ ] For each matched camera, return a flat dict with these fields (mirror the `entities/sensors` shape so the frontend can reuse rendering patterns):
  ```python
  {
      "entity_id": entry.entity_id,
      "name": <friendly_name from hass.states.get(entry.entity_id) or entry.entity_id>,
      "area": <area name via the same entity-area-fallback-to-device-area chain used in websocket_entities_sensors>,
      "device_id": entry.device_id,
      "paired_sensor_entity_ids": [<see below>],
  }
  ```
- [ ] `paired_sensor_entity_ids` scope — entity_ids of entities on this camera's `device_id` matching ALL of:
  - `entry.domain == "binary_sensor"`
  - `entry.config_entry_id == abode_entry.entry_id` (only Abode-managed sensors)
  - `entry.hidden_by is None`
  - `entry.disabled_by is None`
  Sort by entity_id ascending. Empty list is valid (e.g. a camera-only device or a device whose paired sensors are all hidden). The frontend uses this to show "Paired with: Front Door Motion, Front Door Contact" beneath each card; empty list → render nothing.
  Note the deliberate asymmetry with the camera-discovery rule above: the camera is included when *any* co-located Abode entity exists, but `paired_sensor_entity_ids` lists *only* Abode-managed sensors. Third-party sensors paired with this camera under a device grouping aren't shown here — they're not eligible to drive an Abode action anyway, so the list reflects "which Abode sensors can trigger snapshots on this camera."
- [ ] Sort the camera result list alphabetically by `name.lower()`, same convention as `entities/sensors`.
- [ ] Return payload: `{"cameras": [...]}`.

Note: this handler iterates the registry while `entities/sensors` iterates the state machine. The asymmetry is intentional (rationale in the discovery-rule bullet above). Do not refactor `entities/sensors` in this phase to "match" — the duplicate-then-converge convention already established by Phase 2 (open-coded camera resolution in `snapshot.py`) is the project pattern. Either explicitly allow a tiny shared helper for the "Abode device IDs" set if it cleanly reduces duplication, or duplicate the area-resolution chain inline — both are acceptable.

#### Tests — extend `tests/test_websocket_api.py`

- [ ] `test_ws_entities_cameras_empty`: no Abode entries → `[]`.
- [ ] `test_ws_entities_cameras_lists_abode_motion_cameras`: register a device with a `binary_sensor.*` and a `camera.*` both with `platform="abode_security"` (or matching `config_entry_id`); assert the camera is returned with `paired_sensor_entity_ids` containing the binary_sensor.
- [ ] `test_ws_entities_cameras_excludes_unrelated_cameras`: register a `camera.*` on a device that has no Abode entities; assert it is **not** returned.
- [ ] `test_ws_entities_cameras_includes_third_party_camera_co_located_with_abode_sensor`: device has an Abode `binary_sensor.*` plus a `camera.*` from a different integration. Assert the camera is returned. This locks in the discovery contract used by both this tab and the existing `resolve_co_located_camera`.
- [ ] `test_ws_entities_cameras_excludes_hidden_and_disabled`: hide one camera and disable another; assert both are excluded.
- [ ] `test_ws_entities_cameras_sorted_by_name`: register three cameras with names "Zeta", "Alpha", "Mu"; assert the response is alphabetical (case-insensitive).
- [ ] `test_ws_entities_cameras_requires_admin`: non-admin call returns the standard `unauthorized` error (mirror the existing pattern in `TestWebSocketAdminGating` if present).

#### Documentation (End of Sub-Phase A)

- [ ] No user-facing docs yet (Phase 4 owns the user-facing piece in Sub-Phase C).
- [ ] If `docs/ARCHITECTURE.md` has a "WebSocket API" section that enumerates endpoints, add the new one. Otherwise skip.

### Sub-Phase B: Frontend Cameras tab + deep-link routing

Deployable on its own: the tab exists in the panel and renders the camera list. Notification deep-link routing is wired (it parses `?tab=cameras&camera=<entity_id>` and selects/scrolls), but no user-facing automation/blueprint update yet — that's Sub-Phase C. The user could test the URL manually first.

#### Code changes — `frontend/src/`

- [ ] `frontend/src/types.ts`: add
  ```ts
  export interface AbodeCamera {
    entity_id: string;
    name: string;
    area: string | null;
    device_id: string;
    paired_sensor_entity_ids: string[];
  }
  ```
- [ ] `frontend/src/api.ts`: add
  ```ts
  export async function fetchCameras(hass: HomeAssistant): Promise<AbodeCamera[]> {
    const response = await hass.callWS<{ cameras: AbodeCamera[] }>({
      type: 'abode_security/entities/cameras',
    });
    return response.cameras;
  }
  ```
- [ ] `frontend/src/cameras-tab.ts` (new component, mirror the structure of `actions-tab.ts`):
  - `@property({ attribute: false }) hass!: HomeAssistant;`
  - `@property({ attribute: false }) selectedCameraEntityId: string | null = null;` — set by `abode-panel` from the URL query.
  - `@state() private _cameras: AbodeCamera[] = [];`
  - `@state() private _loading = true;`
  - `@state() private _error: string | null = null;`
  - `@state() private _abort: AbortController | null = null;` — match `actions-tab` pattern.
  - `connectedCallback()`: kick off `_loadCameras()`.
  - `_loadCameras()`: abort prior, set loading, call `fetchCameras(this.hass)`, populate `_cameras`, set loading false. On error set `_error`.
  - `updated(changedProps)`: when `selectedCameraEntityId` becomes non-null and a matching card has rendered, scroll-into-view and add a 1.5s highlight CSS class. Guard against scroll loops by only scrolling on prop change, not on re-render.
  - `disconnectedCallback()`: abort.
  - Rendering:
    - Loading: `<div class="loading">Loading cameras…</div>`.
    - Error: `<div class="error">${this._error}</div>` + a Retry button.
    - Empty: `<div class="empty-state">No Abode cameras found. Pair a camera with one of your Abode sensors via Settings → Devices.</div>`
    - List: for each camera, a card containing:
      - Title row: friendly_name + area (`area` rendered as a small grey chip when present).
      - Still image: `<img>` with `src={this._stillUrl(camera)}` and `loading="lazy"`, refreshed every 5s while the tab is visible (use a `setInterval` started in `connectedCallback` and cleared in `disconnectedCallback`; pause via `document.visibilityState === 'hidden'`).
      - Below the image: `Paired with: <comma-separated friendly names of paired_sensor_entity_ids>`.
    - `_stillUrl(camera)`: `/api/camera_proxy/${camera.entity_id}?_=${this._refreshToken}` — `_refreshToken` is a `@state` epoch-ms number bumped by the interval to bust browser cache. The `/api/camera_proxy/` endpoint is auth-gated by HA's frontend session, which the panel already has.
  - Highlight CSS: `.camera-card.highlight { animation: highlight-pulse 1.5s ease-out; } @keyframes highlight-pulse { 0% { box-shadow: 0 0 0 4px var(--primary-color); } 100% { box-shadow: 0 0 0 0 transparent; } }`.

- [ ] `frontend/src/abode-panel.ts`:
  - Extend `_activeTab` type: `'modes' | 'actions' | 'cameras'`.
  - Add a third `<button>` to the tab bar: "Cameras".
  - Parse `window.location.search` **at field-init time** (not in `connectedCallback`) so the panel mounts directly on the target tab — avoids a visible Modes → Cameras flash on deep-link arrival. Pattern:
    ```ts
    private static _initialTabFromUrl(): 'modes' | 'actions' | 'cameras' {
      const tab = new URLSearchParams(window.location.search).get('tab');
      return tab === 'cameras' || tab === 'actions' ? tab : 'modes';
    }
    private static _initialCameraFromUrl(): string | null {
      return new URLSearchParams(window.location.search).get('camera');
    }
    @state() private _activeTab = AbodeConfigurationPanel._initialTabFromUrl();
    @state() private _initialCameraSelection: string | null =
      AbodeConfigurationPanel._initialCameraFromUrl();
    ```
  - When `_activeTab === 'cameras'`, render `<abode-cameras-tab .hass=${this.hass} .selectedCameraEntityId=${this._initialCameraSelection}></abode-cameras-tab>`.
  - On tab switch (the existing `@click=${() => (this._activeTab = ...)}`), set `this._initialCameraSelection = null` whenever the user navigates **away** from Cameras. Reason: when the user later taps back to Cameras, they shouldn't be re-scrolled/re-highlighted on yesterday's notification target — that's surprising. A second deep-link arrival re-triggers the highlight via the same field-init path (browser navigation reloads the panel and re-reads `window.location.search`).
  - Import `./cameras-tab` at the top alongside the other tab imports.

#### Tests — `frontend/src/__tests__/cameras-tab.test.ts` (new)

Mirror the pattern in `actions-tab.test.ts`. Use the existing `createMockHass` helper.

- [ ] `renders empty state when no cameras returned`.
- [ ] `renders a card per camera with name, area chip, and paired-sensors text`.
- [ ] `shows an error and retry button when fetchCameras rejects`.
- [ ] `scrolls and highlights the selected camera when selectedCameraEntityId matches an entry` (use `scrollIntoView` spy and assert the class toggles on then off).
- [ ] `does not scroll or error when selectedCameraEntityId points to a missing/deleted camera` — locks in the resilience contract from Technical Details ("Selected-camera highlight should not require an exact entity_id match").
- [ ] `does not error when paired_sensor_entity_ids is empty`.
- [ ] `refresh interval bumps the still URL cache buster` (advance fake timers, assert `<img>` src query param changed). Use `@sinonjs/fake-timers` if no existing fake-timer pattern is in the test suite — confirm by `grep -r "fakeTimers\|useFakeTimers" frontend/src/__tests__` first; reuse the existing helper if present, install otherwise.
- [ ] `pauses refresh when document.visibilityState is hidden` (set `Object.defineProperty(document, 'visibilityState', {value: 'hidden', configurable: true})`, advance timer, assert no new `_refreshToken`).

#### Tests — extend `frontend/src/__tests__/test-helpers.ts`

- [ ] Default `createMockHass` mock for `abode_security/entities/cameras`: return `{ cameras: [] }` so existing tests don't surface the new tab unintentionally.

#### Tests — extend `actions-tab.test.ts` / `modes-tab.test.ts` if they assert on the panel tab list

- [ ] Search for any test that asserts a specific number of tabs in `abode-panel`; bump from 2 to 3 (likely just one place if any).

#### Build verification (Sub-Phase B local gate)

- [ ] `npm --prefix frontend run lint && npm --prefix frontend run format && npm --prefix frontend run typecheck` — clean.
- [ ] `npm --prefix frontend run test` — all existing tests pass; new cameras-tab tests pass.
- [ ] `npm --prefix frontend run build` — bundle rebuilt; `grep -c "abode-cameras-tab" custom_components/abode_security/www/abode-security-panel.js` returns ≥1.
- [ ] Stage the rebuilt bundle for commit (this is the same pattern the prior commits used; the JS bundle is tracked).

> A phase-wide Build Verification gate runs again after Sub-Phase C — see below.

### Sub-Phase C: Wire the deep-link from notification → tab

> **Hard dependency: Sub-Phase B's rebuilt bundle must be deployed to the target HA before Sub-Phase C's live-automation update.** Sub-Phase C points every future notification tap at `/abode_security?tab=cameras&camera=...`. If B's panel changes are not on the box, every tap dead-ends on a "tab" that doesn't exist. Order is: A → B → deploy → C.

Now the URL `/abode_security?tab=cameras&camera=<entity_id>` opens to the right place. Update the blueprint and docs to use it; update the user's existing live automation via MCP for the next test cycle.

#### Code changes

- [ ] `blueprints/abode_security_notification.yaml`: in both snapshot branches (snapshot+critical, snapshot+non-critical), replace the existing `url:` and `clickAction:` lines (currently set to `"entityId:{{ trigger.event.data.camera_entity_id }}"`) with:
  ```yaml
  # Tap → Abode Security panel's Cameras tab, scrolled/highlighted on
  # the triggering camera. The URL works the same on iOS Companion
  # (`url`) and Android Companion (`clickAction`); set both so the
  # blueprint is platform-agnostic.
  url: "/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"
  clickAction: "/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"
  ```
  Same edit in both snapshot branches; keep them lockstep.
- [ ] `docs/notifications.md`:
  - In the "Minimal Automation" example, replace the `entityId:` line with the new path-based URL (matching the blueprint).
  - Update the post-snippet caveat sentence to drop the `url`/`clickAction` platform asymmetry note (the path form is uniform across both platforms — only the key name differs, and we still set both for explicitness).
  - In the "Filtering by Action" section: no change needed.
  - Add a new short subsection at the end (before Troubleshooting) titled **"Cameras tab"** explaining: the integration ships a Cameras tab in the Abode Security panel that auto-discovers every camera sharing a device with an Abode sensor; the notification deep-links to it via the URL above; live stream is not part of this MVP — taps land on a stills view that auto-refreshes.

#### Live user automation update via MCP

- [ ] Patch `automation.abode_action_notification` (the user's current automation) so the next notification picks up the new path-based URL. Conceptual operation: replace the `url` and `clickAction` values in the snapshot-branch `data.data` with `"/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"`. The home-assistant MCP server exposes tools for this — call `ha_list_resources` first to enumerate them and verify the tool name (the README at line 87 explicitly warns against assuming tool names). The previously-observed names `ha_config_get_automation` and `ha_config_set_automation` (with `python_transform` argument) were in use as of 2026-05-23 but are external to this repo and may have changed; verify before depending on them. If MCP tools are unavailable, fall back to editing the automation YAML via the HA UI manually — same end state.

#### Documentation (End of Sub-Phase C)

- [ ] `docs/ARCHITECTURE.md`: add a one-paragraph note under the existing "Custom panel" section (or under the action-trigger section if no panel section exists) describing the Cameras tab — discovery rule, refresh cadence, deep-link query schema. One paragraph; do not duplicate the `notifications.md` user-facing content.
- [ ] `README.md` "Notifications" section: tiny one-sentence addition mentioning the Cameras tab is the destination for snapshot notifications.

### Build Verification (required before marking phase complete)

- [ ] `./scripts/check.sh` — exits zero (covers ruff, mypy, pyright, pytest including the new cameras endpoint tests).
- [ ] `npm --prefix frontend run lint && npm --prefix frontend run format && npm --prefix frontend run typecheck && npm --prefix frontend run test` — all clean.
- [ ] `npm --prefix frontend run build` — re-run after any final docs/blueprint tweaks, then `git status` shows the bundle is up to date. Confirm `grep -c "abode-cameras-tab" custom_components/abode_security/www/abode-security-panel.js` ≥ 1 and `grep -c "Cameras" custom_components/abode_security/www/abode-security-panel.js` ≥ 1.
- [ ] `uv run python -c "import yaml; yaml.SafeLoader.add_constructor('!input', lambda l, n: f'!input {n.value}'); yaml.safe_load(open('blueprints/abode_security_notification.yaml'))"` exits zero — blueprint still parses after edits.
- [ ] Scan pytest stdout for unraisable exception warnings and never-awaited-coroutine warnings.
- [ ] Mark `status: done` in this file's frontmatter only after all the above pass.

### Manual Verification with MCP Tools

Setup (one-time per dev session):

- [ ] Build the panel bundle (`npm --prefix frontend run build`), deploy via `./scripts/deploy.sh`, restart HA.
- [ ] In the dev HA UI, ensure there's at least one Abode device with both a `binary_sensor.*` and a co-located `camera.*` (the generic-camera fixture pattern from Phase 2 manual verification works).

Verification:

- [ ] Open `http://localhost:8123/abode_security` (or the prod URL via Tailscale). The tab bar shows three tabs: Modes, Actions, Cameras. Click Cameras. Each Abode-related camera renders as a card with a still image refreshing every ~5s.
- [ ] Open `http://localhost:8123/abode_security?tab=cameras&camera=<some-entity-id>`. The panel opens directly on Cameras and scrolls/highlights that camera.
- [ ] Add a new camera (e.g. a second `generic` integration on a device with another Abode sensor). Reload the Cameras tab — the new camera appears without an HA restart.
- [ ] Call `abode_security.fire_test_notification` with a real `action_id` + `binary_sensor.<co-located-with-camera>`. On the phone, tap the notification. The Companion app opens directly to the Cameras tab with the right camera highlighted. (This is the user-visible win.)
- [ ] Tap a sensor that does **not** have a co-located camera (notification-only action). The notification has no `clickAction`/`url` — tapping does the default "open HA" behavior. Confirm it doesn't land on a broken `?camera=null` URL.

## Technical Details

### Why a refetch-on-tab-activate instead of a long-lived `entity_registry_updated` subscription

HA's WS API supports subscribing to `entity_registry_updated` events. We could keep the Cameras list live without any user action. But:
- The tab is not a high-frequency view — users open it when they investigate, not constantly.
- A subscription means non-trivial lifecycle code (subscribe/unsubscribe on connect/disconnect, error recovery, reconnection on HA restart).
- A refetch-on-activate is one line, no lifecycle complexity, and "navigate to Cameras and the new one is there" is the user expectation when the user explicitly added a camera.

If a future phase wants real-time updates (e.g. badge counts on the tab), the subscription model is the right upgrade path. For this MVP, refetch.

### Why `<img>` polling instead of `<ha-camera-stream>`

`<ha-camera-stream>` is HA's built-in element that handles HLS/WebRTC streams with auth tokens, fallback to MJPEG, and stream lifecycle. It works well embedded in Lovelace cards but requires:
- Importing it from `home-assistant-frontend`, which is not in the panel's `package.json` and would couple the panel to a specific HA frontend revision — HA core upgrades that rev the frontend would risk breaking our import.
- Per-camera stream URL fetching via `hass.callWS({type: "camera/stream", entity_id})`.
- Manual cleanup of stream sessions on tab leave to avoid leaking server-side stream connections.

A plain `<img src=/api/camera_proxy/<entity_id>?_=N>` with a 5s cache-buster is ~5 LOC and depends only on HA's stable HTTP API. "Good enough" for the investigative use case, and survives HA core upgrades without bundling a frontend peer dep. Live stream support is real work and belongs in a follow-up phase (`phase-5-live-stream.md`) if there's user demand.

### URL scheme: query params, not path segments

Path: `/abode_security?tab=cameras&camera=<entity_id>` rather than `/abode_security/cameras/<entity_id>`. Two reasons:
1. HA's `panel_custom` routing passes the path after the prefix to the panel as `route.path`; using path segments would require the panel to do its own path parsing. Query params are read once from `window.location.search`.
2. The `?tab=...` form generalizes — future deep-links to specific Actions or Modes views can use the same pattern.

### Cache-busting the `/api/camera_proxy/` URL

HA's `/api/camera_proxy/<entity_id>` returns the current snapshot. The browser caches by URL. To force a refresh, append a query string the server ignores (`?_=<epoch_ms>`). This is a well-worn pattern; the proxy endpoint does not interpret unknown query params.

### Auth on `/api/camera_proxy/`

The panel runs inside an authenticated HA frontend session, so the browser sends the HA auth cookie automatically. No signed URL needed. If a user is somehow not logged in, the `<img>` 401s — the tab should not crash. A simple `onerror` handler showing a "Failed to load" overlay is enough.

### Refresh cadence

5 seconds. Trade-off:
- Faster (1s): the camera proxy hits the integration on every poll; for cloud cameras like Abode's, that's an upstream HTTP request every second per visible camera. Too much, and Abode rate-limits aggressively (per `CLAUDE.md` § "Abode API quirks": polling endpoints return 429 if hit too often).
- Slower (30s): feels stale to a user who just opened the tab to investigate.
- 5s is the same default the HA picture-entity card uses.

For users with many cameras on the tab, all visible at once, this is N parallel polls every 5s — N=5+ can push the Abode cloud rate-limit. A future phase could pause refresh for cards scrolled out of view via `IntersectionObserver`; out of scope here, but flagged so the "but my Abode API got rate-limited" report has a known upgrade path.

### Selected-camera highlight should not require an exact entity_id match

If the URL has `?camera=camera.foo` but `foo` isn't in the returned list (e.g. it was deleted), the tab should still render normally — no highlight, no error, no scroll attempt. This avoids a notification-from-yesterday breaking the experience when devices change.

### Why `paired_sensor_entity_ids` is plural

A single Abode device often hosts a contact sensor **and** a motion sensor (the Abode all-in-one). The frontend should be able to surface all of them so the user can correlate. Empty list is valid (e.g. a camera-only device imported via Phase 2 third-party path) and the UI should handle it (render nothing under the camera card).

## Constraints

- **Do not touch `websocket_entities_sensors` / `websocket_entities_alarms`.** Duplicate the area-resolution chain inline in the new handler if needed. The "duplicate-then-converge" convention already established by Phase 2 (open-coded camera resolution in `snapshot.py`) is the project pattern; a tiny shared `_get_abode_device_ids(hass)` helper is acceptable if it cleanly de-duplicates, but a refactor of the existing handlers expands the diff and risks regressions on a phase that should stay focused.
- **No new external dependencies.** The frontend tab uses Lit (already bundled), the `/api/camera_proxy/` endpoint (built into HA), and standard browser APIs (`URLSearchParams`, `setInterval`, `document.visibilityState`).
- **No backwards-incompatible changes.** This phase adds a tab and a WS endpoint; existing endpoints, events, and the existing panel tabs remain unchanged.
- **Bundle must be rebuilt and committed.** `custom_components/abode_security/www/abode-security-panel.js` is tracked in git. Forgetting to rebuild ships a Cameras tab in the source that doesn't appear in HA — same failure mode as the prior commit's pre-fix bundle.
- **Mode gating is not relevant here.** The Cameras tab is always available regardless of alarm mode; the user opening it to look at their cameras is independent of "is the alarm armed."
- **No PII concerns beyond the existing `/api/camera_proxy/` exposure.** The endpoint is admin-gated by HA; we add no new public surface.
- **No live stream in this phase.** The constraint is explicit so a future implementer doesn't accidentally pull in HLS/WebRTC and triple the scope.

## Out of scope (followups, not this phase)

- Live stream rendering (`<ha-camera-stream>` or similar) — track as a potential `phase-5-live-stream.md`.
- Per-camera notification settings (e.g. "always send critical when the kitchen camera fires") — orthogonal to the tab and lives in the Actions editor.
- A "Snapshots history" tab showing all JPEGs under `/config/www/abode_security_snapshots/` — interesting but a separate feature; the daily purge already bounds the dir.
- Mobile-app push action buttons (e.g. "Acknowledge", "Snooze") — would require richer `actions` payloads in the blueprint and is a notification-UX feature, not a panel one.
- Live badge count on the Cameras tab indicating recently-fired sensor triggers — would require the WS event subscription discussed in "Why refetch-on-tab-activate." If this comes up, that's the obvious upgrade path.
