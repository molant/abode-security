# Action-Triggered Notifications

When an Abode action fires, the integration emits an `abode_security.action_triggered` event enriched with the triggering sensor's context (friendly name, area, device class, prior/new state) and — when the sensor's device also exposes a `camera.*` entity and the system is in `home` or `away` mode — a snapshot URL ready to use as `data.image` in a mobile notification. The integration never calls `notify.*` itself; you wire notifications via your own HA automation or the bundled blueprint.

> ⚠️ **Security note**: Snapshots are written under `/config/www/` and served at `/local/abode_security_snapshots/...` **without authentication**. Anyone with the URL can view the image. If your HA instance is internet-exposed or shared with untrusted users, factor this into your `snapshot_retention_days` setting and be mindful of which URLs you share.

---

## Event Reference

Event type: `abode_security.action_triggered`

All keys are always present in the payload; values are `null` when they cannot be determined (see the table).

| Key | Type | When `null` | Example |
|---|---|---|---|
| `action_id` | str (UUID) | never | `"<uuid-of-your-abode-action>"` — see [Finding your Abode action's UUID](#finding-your-abode-actions-uuid) |
| `action_name` | str | never | `"Front Door Motion"` |
| `triggered_by` | str (entity_id) | never | `"binary_sensor.front_door_motion"` |
| `mode` | str | never | `"home"`, `"away"`, or `"standby"` |
| `alarms_triggered` | list[str] | empty list, never null | `["switch.abode_alarm_panic_alarm"]` |
| `alarms_failed` | list[str] | empty list, never null | `[]` |
| `alarm_outcome` | str | never | `"armed"`, `"partial"`, `"failed"`, `"none"` — see below |
| `alarm_failures` | dict[str, str] | empty dict, never null | `{"switch.abode_alarm_burglar_alarm": "api_error: (400, ...)"}` |
| `severity` | str | never | `"critical"`, `"high"`, `"normal"` — see below |
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

### `alarm_outcome` — did the alarm actually fire?

| Value | Meaning |
|---|---|
| `armed` | Every configured alarm was dispatched successfully. For an Abode manual alarm switch that means the panel accepted it and monitoring was notified; for a third-party switch used as an alarm target it only means `switch.turn_on` succeeded. |
| `partial` | Some raised, some failed. Monitoring may not have been contacted. |
| `failed` | None raised. **No alarm, and your monitoring service was not contacted.** |
| `none` | Notification-only action — no alarm is configured. |

`alarm_failures` maps each failed entity to a reason:

| Reason | Meaning |
|---|---|
| `entity_missing` | The stored entity_id no longer exists. |
| `entity_unavailable` | The switch was unavailable, so Home Assistant never dispatched to it — commonly a dropped Abode SocketIO connection. |
| `entity_wrong_domain` | The stored entity_id is not a `switch.*`, so `switch.turn_on` had nothing to dispatch to. |
| `api_error: …` | Abode rejected the request — e.g. an alarm type it will not raise on demand, see [Manual alarm types](./ARCHITECTURE.md#manual-alarm-types). |

**Always branch on `alarm_outcome` in your automation.** An action whose alarm failed
is otherwise indistinguishable from one that worked, which is exactly how a
"Call the police" action can fire ten times and summon nobody.

### `severity` — how loudly to announce it

Computed by the integration so every automation escalates consistently:

| Value | When |
|---|---|
| `critical` | An alarm was armed, **or** an alarm failed to arm. |
| `high` | `away` mode with no alarm involved. |
| `normal` | Everything else (standby, home-mode notification-only). |

Test fires via `fire_test_notification` are scored the same way as real ones —
pass `mode: away` and you get `high`, which is deliberate: it lets you verify
your escalation setup end to end.

A *failed* alarm is deliberately `critical`, not lesser — you need to know
immediately that the escalation you were counting on did not happen.

---

## Minimal Automation

Copy-paste this into your `automations.yaml` or the Automation editor:

```yaml
alias: Abode action notification
trigger:
  - platform: event
    event_type: abode_security.action_triggered
variables:
  message_text: >-
    {{ trigger.event.data.sensor_friendly_name or trigger.event.data.triggered_by }}
    {{ 'opened' if trigger.event.data.sensor_device_class in ['door', 'window']
       else 'detected motion' if trigger.event.data.sensor_device_class == 'motion'
       else 'triggered' }}
    ({{ trigger.event.data.mode }})
action:
  - choose:
      # Has snapshot → include image + deep-link (snapshot always implies camera).
      - conditions: "{{ trigger.event.data.snapshot_path is not none }}"
        sequence:
          - service: notify.mobile_app_<your_device>
            data:
              title: "{{ trigger.event.data.action_name }}"
              message: "{{ message_text }}"
              data:
                image: "{{ trigger.event.data.snapshot_path }}"
                # Tap → Abode Security panel's Cameras tab, scrolled to
                # the triggering camera. Works on both iOS (`url`) and
                # Android (`clickAction`) Companion; set both for
                # cross-platform parity.
                url: "/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"
                clickAction: "/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"
      # No snapshot, but the camera is known (e.g. snapshot timeout, or standby
      # mode where capture is skipped). Still let the user tap through.
      - conditions: "{{ trigger.event.data.snapshot_path is none and trigger.event.data.camera_entity_id is not none }}"
        sequence:
          - service: notify.mobile_app_<your_device>
            data:
              title: "{{ trigger.event.data.action_name }}"
              message: "{{ message_text }}"
              data:
                url: "/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"
                clickAction: "/abode_security?tab=cameras&camera={{ trigger.event.data.camera_entity_id }}"
    default:
      # No camera at all (sensor isn't paired with one) → bare notification.
      - service: notify.mobile_app_<your_device>
        data:
          title: "{{ trigger.event.data.action_name }}"
          message: "{{ message_text }}"
```

The `choose` block intentionally omits `data.image` when `snapshot_path` is `null` — some notify integrations reject `image: null`. The deep-link (`url`/`clickAction`) is gated on `camera_entity_id`, not on `snapshot_path`, so a notification fired in standby mode (where snapshot capture is skipped) or when the snapshot times out still lets the user tap through to the Cameras tab. The tap-action keys (`url` for iOS Companion, `clickAction` for Android Companion) are honored by the HA Companion mobile app and silently ignored by other notify integrations (Telegram, Pushover, `notify.html5`, etc.), so the same automation works for everyone.

---

## Critical-Alert Variant

For iOS, add a `push` block under `data`:

```yaml
- service: notify.mobile_app_<your_device>
  data:
    title: "{{ trigger.event.data.action_name }}"
    message: "{{ trigger.event.data.sensor_friendly_name or trigger.event.data.triggered_by }} triggered"
    data:
      image: "{{ trigger.event.data.snapshot_path }}"  # omit when null
      push:
        interruption-level: critical
        sound:
          name: default
          critical: 1
          volume: 1.0
```

For Android, use `channel` and `priority` instead:

```yaml
    data:
      image: "{{ trigger.event.data.snapshot_path }}"  # omit when null
      channel: "critical"
      priority: high
      ttl: 0
```

HA passes these through to the Companion app; unsupported keys on the other platform are silently ignored.

Gate them on `severity` so a standby-mode test trip isn't as loud as a real break-in:

```yaml
      push:
        interruption-level: >-
          {{ 'critical' if trigger.event.data.severity == 'critical'
             else 'time-sensitive' if trigger.event.data.severity == 'high'
             else 'active' }}
```

> ⚠️ **Upgrading from an earlier blueprint**: the `critical` yes/no input was
> replaced by `critical_mode` (`auto` / `always` / `never`). Home Assistant
> ignores stored inputs it no longer recognises rather than erroring, so an
> automation that had `critical: true` silently falls back to `auto` — away-mode
> trips become time-sensitive instead of critical. **If you deliberately wanted
> every notification critical, re-open the automation and set
> `critical_mode: always`.** Under `auto`, an alarm that armed *or failed to
> arm* is still critical.

### These two steps are required, or critical alerts silently downgrade

Both platforms accept the keys above and then quietly deliver an ordinary
notification unless you do this once per device:

- **iOS** — grant the Critical Alerts permission: Home Assistant app → Settings →
  Notifications → enable critical alerts. Without it the `critical: 1` sound is
  accepted and ignored, and the alert will not bypass Do Not Disturb or the
  ringer switch.
- **Android** — a notification channel takes its importance from the moment it is
  first created, and never changes afterwards. If you have already received a
  non-critical notification on the `critical` channel, `priority: high` will not
  raise it. Fix it in Android Settings → Apps → Home Assistant → Notifications by
  setting that channel's importance manually, or by clearing the app's channels so
  it is recreated.

Verify with `abode_security.fire_test_notification` (requires the `debug_logging`
option) rather than by walking past a sensor — it exercises the whole path without
arming the panel.

---

## Filtering by Action

To notify only for a specific action, restrict on its `action_id`. See [Finding your Abode action's UUID](#finding-your-abode-actions-uuid) below for how to get the value.

```yaml
alias: Abode — front door only
trigger:
  - platform: event
    event_type: abode_security.action_triggered
condition:
  - condition: template
    value_template: "{{ trigger.event.data.action_id == '<paste-your-action-uuid>' }}"
action:
  - service: notify.mobile_app_<your_device>
    data:
      title: "Front door opened"
      message: "{{ trigger.event.data.sensor_friendly_name }} ({{ trigger.event.data.mode }})"
```

---

## Blueprint

If you just want mobile notifications with snapshots and don't want to write YAML, import the bundled blueprint.

Because `hacs.json` does not declare blueprint distribution, you must import it manually:

1. Go to **Settings → Automations & Scenes → Blueprints**
2. Click **Import Blueprint**
3. Paste this URL:
   ```
   https://raw.githubusercontent.com/molant/abode-security/main/blueprints/abode_security_notification.yaml
   ```
4. Click **Preview** then **Import Blueprint**

The blueprint inputs are:
- **Notify target** (required): the service name, e.g. `notify.mobile_app_iphone`
- **Action filter** (optional): an `action_id` UUID — leave blank to notify for all actions
- **Critical alert** (optional, default `false`): iOS critical alerts bypass Do Not Disturb; Android sets a high-priority channel

---

## Notification-only actions

The **Alarm to trigger** field in the action editor is optional. Pick **None (notification only)** to create an action that fires `abode_security.action_triggered` (with snapshot, area, etc.) but does not arm any switch. Useful for sensors that should notify without escalating, and for testing the notification path end-to-end without setting off the panel.

In the event payload, `alarms_triggered` and `alarms_failed` are both empty lists for notification-only actions.

---

## Testing without arming the panel

The `abode_security.fire_test_notification` action runs the full event-fire and snapshot-capture path for a chosen Abode action — but skips the alarm `switch.turn_on` calls, the mode gate, and the debounce. It writes a real JPEG under `/config/www/abode_security_snapshots/` (when the sensor has a co-located camera) and fires a real `abode_security.action_triggered` event, so your blueprint or automation reacts exactly as it would for a real trigger.

> **Don't add a second trigger to your automation.** Calling this action fires the same `abode_security.action_triggered` event your existing automation already listens for — it's a "1-click fake trigger," not a separate code path.

**Opt-in:** the action refuses to run unless **debug logging** is enabled in the integration options (**Settings → Devices & Services → Abode Security → Configure → Debug logging**).

Call it from **Developer Tools → Actions** (called "Services" in older HA versions):

```yaml
action: abode_security.fire_test_notification
data:
  action_id: <paste your Abode action's UUID here — see below>
  sensor_entity_id: binary_sensor.front_door
  mode: home  # optional — defaults to "home"; snapshot is forced regardless
```

The event payload mirrors a real trigger except `alarms_triggered` / `alarms_failed` are empty lists. Use it to verify your notification target, critical-alert configuration, and image rendering without arming the system or walking past a sensor.

### Finding your Abode action's UUID

The action `id` field is a UUID generated when you create the action in the Abode Security panel.

**Easiest:** with **Debug logging** enabled in the integration options, every row in the Abode Security panel's Actions tab gets a **copy** icon (next to the test/edit/delete buttons). Click it to copy the action's UUID to your clipboard. The button is intentionally hidden when debug logging is off so it doesn't clutter the panel for everyday use.

**Fallback** (if you can't enable debug logging for some reason):

1. Open **Developer Tools → Events**.
2. In the **Listen to events** box, type `abode_security.action_triggered` and click **Start listening**.
3. Trigger the action once for real (walk past the sensor, or toggle a `binary_sensor` to `on` from Developer Tools → States).
4. The event appears in the listener with the full payload — copy the `action_id` value.

Keep that UUID handy; you'll need it for the action filter in your automation or blueprint, and for the `fire_test_notification` action above.

---

## Cameras tab

The Abode Security panel (`/abode_security`) includes a **Cameras** tab that lists every camera entity in Home Assistant. The integration is camera-source-agnostic — Abode, Unifi Protect, generic, or any other integration's cameras are all valid deep-link targets, because any HA sensor can drive an Abode action and the snapshot pipeline already resolves whatever camera shares a device with the triggering sensor.

Each card renders the camera with HA's native `<ha-camera-stream>` element — the same renderer used by the picture-entity Lovelace card with `camera_view: auto` — so auth, HLS/WebRTC fallback, and stream lifecycle are handled by Home Assistant. Tapping a card opens HA's standard more-info dialog for that camera (equivalent to `tap_action: more-info` in a picture-entity card), where the full live stream is available.

When you tap a snapshot notification generated by the blueprint or the minimal automation above, the Companion app opens `/abode_security?tab=cameras&camera=<entity_id>`. The panel loads directly on the Cameras tab, scrolls/highlights the triggering camera, and **automatically opens its more-info dialog** so you land on the live stream without an extra tap. Dismissing the dialog leaves you on the Cameras grid with that camera card still highlighted.

---

## Troubleshooting

### I'm not getting `snapshot_path` — why?

- Is `mode` `standby`? Snapshots are skipped in standby by design.
- Does the triggering sensor's HA device also expose a `camera.*` entity? Check **Settings → Devices** → your device → **Entities** tab — a camera entry must appear there.
- Is `snapshot_error` set? Common values:
  - `"timeout"` — the `camera.snapshot` service took more than 3 seconds
  - `"service_error: ..."` — HA rejected the snapshot call (check camera entity state)
  - `"io_error: ..."` — disk write failed
- Is `/config/www/abode_security_snapshots/` writable by the HA process?

### The notification arrives but the image doesn't load

- Is the `/local/...` URL reachable from the Companion app? It must be on the same LAN, or HA must have a remote URL configured (via Nabu Casa or a reverse proxy).
- Has the snapshot already been purged? The default retention is 30 days, but if you set `snapshot_retention_days` to `1`, a day-old notification will show a broken image.

### Snapshots are filling my disk

- Lower `snapshot_retention_days` in the integration options (**Settings → Devices & Services → Abode Security → Configure**). The minimum is 1 day.

---

## Notifying on Schedule Events

When a scheduled arm or disarm fires (or is skipped/failed), the integration emits one of three HA events. You can build automations on top of them exactly as you would for `action_triggered`.

| Event | When it fires | Key payload fields |
|---|---|---|
| `abode_security.schedule_fired` | Arm or disarm succeeded | `schedule_id`, `schedule_name`, `action` ("arm"/"disarm"), `target_mode`, `fired_at` |
| `abode_security.schedule_skipped` | Arm/disarm skipped (Away active, already Home, panel unavailable, or manual override) | `schedule_id`, `schedule_name`, `action`, `reason`, `skipped_at` |
| `abode_security.schedule_failed` | All 4 retries exhausted | `schedule_id`, `schedule_name`, `action`, `error`, `attempts`, `failed_at` |

### Example automation — notify on arm

```yaml
alias: "Notify: schedule armed Home mode"
trigger:
  - platform: event
    event_type: abode_security.schedule_fired
    event_data:
      action: arm
action:
  - service: notify.mobile_app_<your_phone>
    data:
      title: "Abode armed"
      message: "Schedule '{{ trigger.event.data.schedule_name }}' armed Home mode."
```

### Example automation — alert on schedule failure

```yaml
alias: "Alert: schedule failed to fire"
trigger:
  - platform: event
    event_type: abode_security.schedule_failed
action:
  - service: notify.mobile_app_<your_phone>
    data:
      title: "Schedule failed!"
      message: >
        '{{ trigger.event.data.schedule_name }}' failed to
        {{ trigger.event.data.action }} after {{ trigger.event.data.attempts }}
        attempts. Error: {{ trigger.event.data.error }}
```

The bundled blueprint (`blueprints/abode_security_notification.yaml`) covers the `action_triggered` pattern. For schedule events, copy and adapt the snippets above — the payload shape is analogous.

### Skip reasons

The `reason` field on `schedule_skipped` events takes one of six values:

| Reason | Meaning |
|---|---|
| `away_active` | Panel was `armed_away`; arm and disarm both skipped |
| `already_home` | Panel already `armed_home`; arm skipped but disarm still fires later |
| `panel_unavailable` | Panel in an intermediate state or entity not registered |
| `manual_override` | Panel left `armed_home` via a non-schedule context (user changed mode manually) |
| `reconcile_window_elapsed` | HA restarted after the disarm window had already passed |
| `reconcile_panel_not_home` | HA restarted mid-window but panel was no longer Home |
