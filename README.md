# Abode Security for Home Assistant

A drop-in replacement for the built-in Abode integration that lets you **trigger Abode alarms and actions from _any_ Home Assistant sensor or camera** — and edit your modes, actions, and schedules from a visual panel, no YAML required.

[![GitHub Release](https://img.shields.io/github/v/release/molant/abode-security?label=Version)](https://github.com/molant/abode-security/releases)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/molant/abode-security/actions/workflows/tests.yaml/badge.svg)](https://github.com/molant/abode-security/actions/workflows/tests.yaml)

## Install

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=molant&repository=abode-security&category=integration)

Click the button above to add the repository to HACS in one step, then **Download** and restart Home Assistant. Finally add the integration from **Settings → Devices & Services → Add Integration → Abode Security**.

<details>
<summary>Manual install</summary>

Copy `custom_components/abode_security` into your Home Assistant `custom_components/` directory and restart. Then add the integration as above.
</details>

## Why this integration?

The built-in Abode integration can only react to Abode's own sensors. This one lets **any Home Assistant entity** drive your alarm — a UniFi doorbell, a Zigbee motion sensor, a `template` binary sensor, anything HA can see.

| Feature | Built-in Abode | This integration |
|---|:---:|:---:|
| Abode devices (sensors, cameras, locks, alarm panel) | ✅ | ✅ |
| Trigger alarms & actions from **any HA sensor or camera** | ❌ | ✅ |
| Visual editor for modes, actions & schedules | ❌ | ✅ |
| Manual alarm trigger (panic / medical / CO / smoke / burglar) | ❌ | ✅ |
| Rich notifications with camera snapshots | ❌ | ✅ |
| Scheduled arming / disarming | ❌ | ✅ |

## Screenshots

| Modes & schedules | Action editor | Dispatch settings |
|---|---|---|
| [![Modes, actions and schedules](images/modes.png)](images/modes.png) | [![Editing an action with any HA sensor](images/edit-action.png)](images/edit-action.png) | [![Alarm dispatch configuration](images/alarm-configuration-settings.png)](images/alarm-configuration-settings.png) |

Define **modes** (Home / Standby / Away), attach **actions** that watch any HA sensors and optionally arm the panel, and set **schedules** for automatic arming — all from the integration's panel at `/abode_security`.

## Documentation

- [Configuration & actions](docs/configuration.md) — setup options and the full service/action reference
- [Notifications](docs/notifications.md) — camera-snapshot notifications and the bundled blueprint
- [Troubleshooting](docs/troubleshooting.md) — common issues, diagnostics, and FAQ
- [Architecture](docs/ARCHITECTURE.md) — design and data flow

## Acknowledgments

Builds on [jaraco.abode](https://github.com/jaraco/abode) and the original Home Assistant Abode integration, with added async support, a custom actions system, and the visual configuration panel.

## License

[MIT](LICENSE)
