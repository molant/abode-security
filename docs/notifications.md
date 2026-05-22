# Action-Triggered Notifications

When an Abode action fires, the integration emits an `abode_security.action_triggered` event enriched with the triggering sensor's context (friendly name, area, device class, prior/new state) and — when the sensor's device also exposes a `camera.*` entity and the system is in `home` or `away` mode — a snapshot URL ready to use as `data.image` in a mobile notification. The integration never calls `notify.*` itself; you wire notifications via your own HA automation or the bundled blueprint.

> ⚠️ **Security note**: Snapshots are written under `/config/www/` and served at `/local/abode_security_snapshots/...` **without authentication**. Anyone with the URL can view the image. If your HA instance is internet-exposed or shared with untrusted users, factor this into your `snapshot_retention_days` setting and be mindful of which URLs you share.

---

## Event Reference

Event type: `abode_security.action_triggered`

All keys are always present in the payload; values are `null` when they cannot be determined (see the table).

| Key | Type | When `null` | Example |
|---|---|---|---|
| `action_id` | str (UUID) | never | `"7f3b6a2c-1234-5678-abcd-ef0123456789"` |
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

---

## Minimal Automation

Copy-paste this into your `automations.yaml` or the Automation editor:

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

The `choose` block intentionally omits `data.image` when `snapshot_path` is `null` — some notify integrations reject `image: null`.

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

---

## Filtering by Action

To notify only for a specific action (e.g. the front door action with ID `7f3b6a2c-...`):

```yaml
alias: Abode — front door only
trigger:
  - platform: event
    event_type: abode_security.action_triggered
condition:
  - condition: template
    value_template: "{{ trigger.event.data.action_id == '7f3b6a2c-1234-5678-abcd-ef0123456789' }}"
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
