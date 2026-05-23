---
status: done
phase: 5
feature: notifications
title: Cameras tab — list every HA camera, ha-camera-stream rendering, auto more-info on deep-link
---

# Phase 5: Cameras tab — list every HA camera + picture-entity-style rendering

Three coupled changes to the Cameras tab shipped in Phase 4:

1. **Drop the Abode-only filter.** The tab now lists every camera entity in HA, regardless of source integration. Phase 4's strict "must share a device with an Abode entity" rule hid the user's Unifi Protect cameras — wrong, because the rest of the integration (snapshot pipeline, action triggers, event payload) is camera-source-agnostic.
2. **Replace `<img>` polling with `<ha-camera-stream>`.** The Phase 4 still-image-with-cache-buster approach failed to load on Unifi Protect cameras (auth path mismatch) and rendered noisy "Failed to load image" placeholders. Switching to HA's native `<ha-camera-stream>` — the same element picture-entity uses with `camera_view: auto` — delegates auth, HLS/WebRTC fallback, and stream lifecycle to HA, matching what already works in the user's `/wall-ipad/security` dashboard.
3. **Auto-open more-info on deep-link arrival.** Tapping a notification now lands the user directly on the live-stream popup. The Cameras grid is rendered behind the popup so dismissing it leaves the user on the scrolled/highlighted card. Tapping any card also dispatches `hass-more-info`, matching `tap_action: more-info` on picture-entity.

## Context

Phase 4 ([./phase-4-cameras-tab.md](./phase-4-cameras-tab.md)) deliberately built `<img>`-polling with strict Abode-paired discovery, citing:

- "live stream is real work — defer to a follow-up phase" (Technical Details, "Why `<img>` polling instead of `<ha-camera-stream>`").
- "surfacing every camera in HA that happens to share a device with anything would dilute the panel's purpose" (Context, discovery-rule rationale).

Both turned out to be the wrong defaults for this integration:

- On a real Unifi Protect setup, `/api/camera_proxy/<entity>` 401s in the panel's iframe context (auth path issue specific to certain camera integrations) — the polling approach showed nothing but "Failed to load image" placeholders.
- On a real Unifi Protect device, the `binary_sensor.*` entity count per camera is 20+ (detection features, overlay toggles, status sensors). The `paired_sensor_entity_ids` hint becomes a wall of text — worse than no hint.
- "Land on the camera stream" is the actual user goal; a still snapshot is the consolation prize a live stream gives when the connection fails.

The user explicitly asked for parity with their existing picture-entity dashboard layout (`camera_view: auto`, `tap_action: more-info`) and for notifications to "open the more-info automatically." This phase implements that.

`<ha-camera-stream>` is registered globally by HA's frontend bundle; it's resolvable from custom panels without an import. Lit's `html` template accepts the unknown element name and the browser binds it at runtime once the HA frontend has loaded (it always has, by the time the panel mounts).

`paired_sensor_entity_ids` is dropped entirely from the WS response — it was the only field that justified the larger response shape, and the picture-entity-style card has no place for it.

## Structure

```
custom_components/abode_security/
  websocket_api.py               # modify: drop Abode-only filter + paired_sensor_entity_ids field

frontend/src/
  cameras-tab.ts                 # rewrite: <ha-camera-stream> rendering, drop polling/visibility/
                                 # image-error/paired-sensors, add tap → more-info, deep-link →
                                 # auto more-info
  types.ts                       # modify: AbodeCamera = { entity_id, name, area }

frontend/src/__tests__/
  cameras-tab.test.ts            # rewrite: drop polling/visibility/paired tests, add tap and
                                 # deep-link more-info tests

custom_components/abode_security/www/
  abode-security-panel.js        # REBUILD via `npm --prefix frontend run build`

tests/
  test_websocket_api.py          # modify: drop paired_sensor_entity_ids assertions, simplify
                                 # abode_motion_cameras test, invert excludes-unrelated, add
                                 # no-device test

docs/
  notifications.md               # modify: rewrite "Cameras tab" section
  ARCHITECTURE.md                # modify: rewrite Cameras paragraph
  README.md                      # modify: one-sentence adjustment
```

## Implementation Checklist

### Backend — `custom_components/abode_security/websocket_api.py`

- [x] Remove the `abode_entry` lookup and `abode_device_ids` set computation from `websocket_entities_cameras`.
- [x] Drop the `if entry.device_id not in abode_device_ids: continue` filter.
- [x] Drop the `paired_sensor_entity_ids` computation and the corresponding response key.
- [x] Drop the `device_id` field from the response (the frontend no longer needs it).
- [x] Update the handler docstring to describe the new contract (lists every camera; identity + display metadata only; frontend uses HA's native stream renderer + more-info dialog).
- [x] Keep guards: `entry.domain == "camera"`, `hidden_by is None`, `disabled_by is None`. Keep area-resolution and alphabetical sort.

### Backend tests — `tests/test_websocket_api.py`

- [x] `test_ws_entities_cameras_empty` — docstring updated; assertion unchanged.
- [x] `test_ws_entities_cameras_lists_abode_motion_cameras` — simplified: register a camera, assert it's returned with name. No paired-sensor setup or assertion.
- [x] `test_ws_entities_cameras_lists_unrelated_cameras` (renamed from `excludes_unrelated_cameras`): unrelated camera is now returned.
- [x] `test_ws_entities_cameras_lists_camera_with_no_device` — new: camera with `device_id is None` returned.
- [x] `test_ws_entities_cameras_includes_third_party_camera_co_located_with_abode_sensor` — kept; paired-sensor assertion removed.
- [x] `test_ws_entities_cameras_excludes_hidden_and_disabled` — unchanged.
- [x] `test_ws_entities_cameras_sorted_by_name` — unchanged.
- [x] `test_ws_entities_cameras_requires_admin` — unchanged.

### Frontend type — `frontend/src/types.ts`

- [x] `AbodeCamera` reduced to `{ entity_id, name, area }`.

### Frontend tab — `frontend/src/cameras-tab.ts` (rewrite)

- [x] Drop `_refreshToken`, `_imageErrors`, `_refreshInterval`, `_startRefresh`, `_stopRefresh`, `_handleImageError`, `_stillUrl`, `_pairedSensorNames`.
- [x] Render each card as a `<ha-camera-stream allow-exoplayer muted .hass=${this.hass} .stateObj=${this.hass.states?.[camera.entity_id]}></ha-camera-stream>` inside a clickable `.camera-card` with header (name + area chip).
- [x] Tap (`@click`) and `Enter`/`Space` key handlers on the card dispatch `hass-more-info` (`bubbles: true, composed: true`, `detail: { entityId }`).
- [x] On deep-link arrival (`selectedCameraEntityId` set, matching camera present in `_cameras`, not yet auto-opened for this target), dispatch the same `hass-more-info` event once. Reset the "already auto-opened" guard when `selectedCameraEntityId` changes so a fresh deep-link re-fires.
- [x] Keep `_scrollToSelected` and the highlight CSS so the grid is in a useful state when the user dismisses the popup.
- [x] Add `role="button"` + `tabindex="0"` on the card and a `:hover` shadow so keyboard/mouse users get the affordance.

### Frontend tests — `frontend/src/__tests__/cameras-tab.test.ts` (rewrite)

- [x] Remove the polling-interval and visibility-pause tests (no longer applicable).
- [x] Remove the paired-sensors rendering and empty-paired-sensors tests (the field is gone).
- [x] Empty-state test: assertion text now `'No cameras found in Home Assistant'`.
- [x] Card-rendering tests: name, area chip (set / null cases).
- [x] New test: `renders an ha-camera-stream element per camera` — asserts the element exists in the shadow DOM (the custom element itself isn't registered in tests, but Lit creates the unknown element fine).
- [x] New test: `tap on a card opens the more-info dialog` — clicks the card and asserts a `hass-more-info` event with the right detail / bubbles / composed.
- [x] New test: `deep-link arrival auto-opens more-info` — assert fires once when the selected camera is in the list; second update doesn't re-fire; selecting a missing entity does not fire.
- [x] Keep: error-state-with-retry, scroll-and-highlight-on-deep-link, missing-camera-does-not-error.

### Documentation

- [x] `docs/notifications.md` — "Cameras tab" section rewritten: every-camera discovery, picture-entity-style cards with `<ha-camera-stream>`, tap → more-info, notification auto-opens more-info.
- [x] `docs/ARCHITECTURE.md` — Cameras paragraph rewritten to match.
- [x] `README.md` — one-sentence adjustment: "lists every camera in HA" framing.
- [x] `docs/notifications.md` event-payload table (`camera_entity_id` row) — no change; event behavior is unchanged.

### Build Verification

- [x] `./scripts/check.sh` — ruff + mypy + pyright + pytest pass.
- [x] `npm --prefix frontend run lint && npm --prefix frontend run format && npm --prefix frontend run typecheck && npm --prefix frontend run test` — clean (run via `check.sh`).
- [x] `npm --prefix frontend run build` — bundle rebuilt.
- [x] `grep -c "No cameras found in Home Assistant" custom_components/abode_security/www/abode-security-panel.js` ≥ 1.
- [x] `grep -c "ha-camera-stream" custom_components/abode_security/www/abode-security-panel.js` ≥ 1.
- [x] `grep -c "No Abode cameras found" custom_components/abode_security/www/abode-security-panel.js` == 0.

### Manual Verification

- [ ] Deploy the bundle, restart HA.
- [ ] Open `/abode_security` → **Cameras**. Unifi Protect (and any other) cameras render with live stream (no "Failed to load image"), matching what you see in the `/wall-ipad/security` dashboard.
- [ ] Tap any card → HA's more-info dialog opens for that camera with the full live stream.
- [ ] Open `/abode_security?tab=cameras&camera=<unifi_camera_entity_id>` directly — panel mounts on Cameras, scrolls/highlights the target card, and the more-info dialog auto-opens. Dismissing the dialog leaves the highlighted card visible.
- [ ] Trigger an action whose sensor is co-located with a Unifi camera (`abode_security.fire_test_notification`) — notification tap opens directly into that camera's stream.

## Out of scope

- No change to the snapshot pipeline or the event payload — `resolve_co_located_camera` already accepts any camera, and the event's `camera_entity_id` already reflects that.
- No per-action explicit camera selection — co-location auto-discovery is sufficient for current use.
- No fallback when the popup is dismissed quickly (e.g. re-opening on a second deep-link with the same entity). The auto-open guard resets on `selectedCameraEntityId` change; rapid identical-URL re-arrival is not a real flow (browsers consolidate it).

## Why this is a separate phase, not an edit to phase-4

Phase 4 shipped, then ran in production and exposed both the Abode-only filter and the still-image-polling as wrong defaults for the actual use case. Recording the reversal as a separate phase keeps Phase 4's historical rationale intact (it was a defensible choice given the spec assumptions) and makes the cause-and-effect chain readable in `git log` and the spec folder.
