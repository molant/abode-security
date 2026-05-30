# Configuration

[← Back to README](../README.md)

## Initial setup

Add the integration from **Settings → Devices & Services → Add Integration → Abode Security**. You'll be prompted for:

- **Abode Email** — your Abode account email
- **Abode Password** — your Abode account password
- **Enable Polling** — poll the Abode API for updates (default: on)

> Two-factor authentication is not currently supported.

## Options

After setup, open the integration's **Configure** dialog to tune:

- **Polling Interval** (15–120 s, default 30) — how often to check for updates. Lower = more real-time but higher API load.
- **Enable Events** (default on) — use event-based updates via SocketIO when available, reducing polling load.
- **Retry Count** (1–5, default 3) — retries for failed API calls.
- **Debug logging** — required to use `fire_test_notification` (see below).

## Modes, actions & schedules

The integration ships a visual panel at `/abode_security` with three tabs:

- **Modes** — Home, Standby, and Away. Switch the active mode and see which actions each mode runs.
- **Actions** — rules that watch one or more **Home Assistant sensors** (any entity, not just Abode), wait an optional delay, and optionally arm an Abode alarm (burglar, panic, medical, smoke/CO, etc.) or fire a notification-only event.
- **Cameras** — every camera entity in Home Assistant, so snapshot notifications can deep-link to the right one regardless of source integration.

**Home schedules** let you enable automatic arming/disarming on a weekly timetable.

## Actions (services)

> Home Assistant renamed "services" to "actions" in the UI; YAML accepts either `service:` or `action:`. Call these from **Developer Tools → Actions**.

### `abode_security.trigger_alarm`
Trigger a manual alarm. `alarm_type` is one of `PANIC`, `SILENT_PANIC`, `MEDICAL`, `CO`, `SMOKE_CO`, `SMOKE`, `BURGLAR`.

```yaml
action: abode_security.trigger_alarm
data:
  alarm_type: PANIC
```

### `abode_security.acknowledge_alarm`
Acknowledge a security event in the timeline.

```yaml
action: abode_security.acknowledge_alarm
data:
  timeline_id: "12345"
```

### `abode_security.dismiss_alarm`
Dismiss a security event.

```yaml
action: abode_security.dismiss_alarm
data:
  timeline_id: "12345"
```

### `abode_security.trigger_automation`
Trigger an Abode automation by its switch entity.

```yaml
action: abode_security.trigger_automation
data:
  entity_id: switch.my_abode_automation
```

### `abode_security.enable_test_mode` / `disable_test_mode`
Prevent (or re-enable) dispatch notifications during system testing.

```yaml
action: abode_security.enable_test_mode
```

### `abode_security.fire_test_notification` (debug)
Run the snapshot-capture + `abode_security.action_triggered` event path for a chosen action without arming the panel. Requires **Debug logging** enabled in options.

```yaml
action: abode_security.fire_test_notification
data:
  action_id: <your Abode action's UUID>
  sensor_entity_id: binary_sensor.front_door
  mode: home  # optional — standby/home/away, default home
```

See [notifications.md](./notifications.md) for full usage and how to find an action's UUID.
