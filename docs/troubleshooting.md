# Troubleshooting

[← Back to README](../README.md)

## Common issues

**Integration not appearing after installation**
- Make sure you restarted Home Assistant completely after downloading.
- Confirm the integration files live under `custom_components/abode_security/`.

**Devices not appearing**
- Check the Home Assistant logs for errors.
- Verify your Abode credentials are correct and the account has devices assigned.

**Slow responses**
- Lower the polling interval in the integration options (15–30 s), or rely on event updates.
- Check Home Assistant system resources.

**A sensor shows `unavailable` instead of `off`**
- Contact and motion sensors report `unavailable` when the device itself stops
  reporting — an `Offline` status or a `no_response` fault — because its last
  known status is stale, not a reading of "closed". Showing it as `off` is what
  used to let an offline blip on an open window look like a fresh
  `off` → `on` activation and fire an alarm action.
- Search the log for `stopped reporting` to see how often it happens and why:
  `Abode sensor Front Door stopped reporting (status=Offline, no_response=False)`.
- Frequent flapping usually means a weak RF link or a low battery — check the
  sensor's distance from the panel, and its `battery_low` attribute while it is
  reporting (Home Assistant hides entity attributes during the `unavailable`
  half of a flap).

**Authentication errors**
- Verify your Abode password.
- Two-factor authentication is not currently supported.
- Re-authenticate the integration if needed.

## Diagnostics

1. Go to **Settings → Devices & Services → Abode Security**.
2. Open the three-dot menu and select **Download diagnostics**.

The file includes connection status, device inventory, automation status, system capabilities, and any error information — handy when filing an issue.

## FAQ

**Can it trigger an alarm from a non-Abode sensor?**
Yes — that's the point. Create an action in the `/abode_security` panel and pick any Home Assistant sensor as the trigger.

**Does it replace the built-in Abode integration?**
Yes. Remove the built-in one before adding this to avoid duplicate entities.

**Why am I seeing 429 errors in the logs?**
Abode's polling endpoints rate-limit aggressively. Increase the polling interval and keep event updates enabled.

## Known limitations

- No two-factor authentication support.
- Some advanced Abode features are not exposed by the underlying library.

Still stuck? [Open an issue](https://github.com/molant/abode-security/issues) with your diagnostics attached.
