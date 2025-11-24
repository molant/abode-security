# Troubleshooting Guide - Abode Security Integration

Comprehensive troubleshooting guide for common issues with the Abode Security integration.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Error Messages](#error-messages)
- [Collecting Logs](#collecting-logs)
- [Using Diagnostics](#using-diagnostics)
- [Getting Help](#getting-help)
- [FAQ](#faq)

## Quick Diagnostics

Before diving into specific issues, try these quick diagnostic steps:

### 1. Check Integration Status

```yaml
Developer Tools → Services → abode_security
```

If no services appear, the integration isn't loaded properly.

### 2. Download Diagnostics

1. Go to **Settings** → **Devices & Services** → **Abode Security**
2. Click the three-dot menu
3. Select **Download Diagnostics**
4. Save the file

The diagnostic file contains:
- Configuration status
- Device information
- Connection status
- API response times
- Error logs

### 3. Check Home Assistant Logs

```yaml
Settings → System → Logs
```

Search for:
- "abode_security" - integration logs
- "ERROR" - error messages
- "WARNING" - warnings

### 4. Reload the Integration

1. Go to **Settings** → **Devices & Services** → **Abode Security**
2. Click the three-dot menu
3. Click **Reload**
4. Wait for reload to complete

## Common Issues

### Issue: Integration Not Appearing

**Symptoms:**
- Integration doesn't show up when searching
- "No matching integrations found"

**Diagnosis:**
1. Check file is in correct location:
   ```bash
   ls -la custom_components/abode_security/manifest.json
   ```

2. Verify manifest.json syntax:
   ```bash
   python3 -m json.tool custom_components/abode_security/manifest.json
   ```

3. Check Home Assistant logs for syntax errors

**Solutions:**
1. Verify `manifest.json` exists and has correct `domain: abode_security`
2. Check file encoding (must be UTF-8)
3. Restart Home Assistant completely
4. Clear browser cache
5. Try in incognito/private mode

---

### Issue: Authentication Failures

**Symptoms:**
- "Invalid credentials" error
- "Unable to authenticate" message
- Integration won't initialize

**Diagnosis:**
1. Test credentials directly:
   - Visit https://my.abode.com
   - Log in with provided email/password
   - Verify success

2. Check for account issues:
   - Account locked
   - Password expired
   - 2FA enabled

**Solutions:**
1. **Verify credentials**
   - Ensure email is typed correctly
   - Ensure password is entered exactly
   - Check for caps lock

2. **Disable 2FA temporarily**
   - 2FA is not currently supported
   - Disable in Abode account settings
   - Authenticate again

3. **Reset password**
   - Go to https://my.abode.com/password-reset
   - Create new password
   - Update in Home Assistant

4. **Check account status**
   - Ensure account is not locked
   - Verify account is active
   - Check for service outages

---

### Issue: Devices Not Appearing

**Symptoms:**
- No devices listed after configuration
- "No entities" message
- Integration configured but no switches/sensors

**Diagnosis:**
1. Check device assignment in Abode account:
   - Log into Abode app/website
   - Verify devices are assigned to account
   - Check device status (online/offline)

2. Check Home Assistant logs:
   - Look for device-related errors
   - Check API response messages

3. Download diagnostics:
   - Check device count in diagnostic file
   - Verify device types are recognized

**Solutions:**
1. **Verify devices in Abode account**
   - Log into https://my.abode.com
   - Go to Devices section
   - Ensure all devices show as online
   - Reassign devices if needed

2. **Reload integration**
   - Go to Settings → Devices & Services → Abode Security
   - Click three-dot menu
   - Click Reload
   - Wait 10 seconds for devices to appear

3. **Restart Home Assistant**
   - Settings → System → Restart
   - Wait for complete startup
   - Check entities again

4. **Remove and re-add integration**
   - Settings → Devices & Services → Abode Security
   - Click three-dot menu
   - Click Delete
   - Re-add the integration

---

### Issue: Slow Response/Updates

**Symptoms:**
- Updates take a long time
- Entities don't update for minutes
- Clicking buttons takes time to respond

**Diagnosis:**
1. Check polling interval:
   - Settings → Devices & Services → Abode Security → Options
   - Note current polling interval

2. Check network connectivity:
   - Home Assistant → Settings → System → About
   - Check "Update available" (indicates network access)

3. Check API status:
   - Visit https://status.goabode.com/
   - Verify no service outages

**Solutions:**
1. **Increase polling interval**
   - Go to Options
   - Change polling interval to 60-90 seconds
   - May reduce update speed but improves load

2. **Reduce polling interval**
   - If updates are too slow
   - Change polling interval to 15-30 seconds
   - May increase API usage

3. **Enable events**
   - Go to Options
   - Ensure "Enable Events" is True
   - Restart integration

4. **Check Home Assistant resources**
   - Monitor CPU usage
   - Check available memory
   - Stop unnecessary services

5. **Check network**
   - Ping Abode API: `ping api.goabode.com`
   - Check latency
   - Verify firewall rules

---

### Issue: Frequent Disconnections

**Symptoms:**
- Integration repeatedly connects/disconnects
- "Connection lost" messages
- Entities become unavailable frequently

**Diagnosis:**
1. Check network stability:
   ```bash
   ping -c 100 api.goabode.com
   ```
   Look for packet loss > 5%

2. Check Home Assistant logs:
   - Filter for "abode_security"
   - Note disconnect patterns

3. Check firewall/network:
   - Verify outbound access to api.goabode.com
   - Check for ISP throttling
   - Test from different network

**Solutions:**
1. **Increase retry count**
   - Go to Options
   - Increase "Retry Count" to 4-5
   - May help with network instability

2. **Increase polling interval**
   - Less frequent polling = fewer connection attempts
   - Try 60-120 seconds

3. **Check network stability**
   - Restart router
   - Check for WiFi interference
   - Use wired connection if possible

4. **Check firewall**
   - Verify api.goabode.com is whitelisted
   - Check for VPN interference
   - Test with VPN disabled

---

### Issue: High CPU/Memory Usage

**Symptoms:**
- Home Assistant running slow
- CPU usage very high
- Memory usage increasing constantly

**Diagnosis:**
1. Identify if Abode integration is cause:
   - Settings → System → Logs
   - Search for "ERROR" and "WARNING"
   - Check for excessive API calls

2. Check automations:
   - Check for runaway automations
   - Look for frequent service calls

3. Check polling:
   - Verify polling interval is reasonable
   - Check if entities are updating excessively

**Solutions:**
1. **Increase polling interval**
   - Reduce update frequency
   - Try 60-120 seconds

2. **Review automations**
   - Look for automations running very frequently
   - Disable if necessary
   - Test individually

3. **Disable unused entities**
   - Settings → Devices & Services → Entities
   - Hide/disable unused entity types
   - Restart integration

4. **Monitor resource usage**
   - Use Home Assistant GUI
   - Check System → System Monitor
   - Identify peak usage times

## Error Messages

### "Invalid Credentials"

**Cause:** Email/password is incorrect or account issue

**Solutions:**
- Verify email is correct (case-sensitive)
- Verify password is correct (case-sensitive)
- Ensure no 2FA is enabled
- Try resetting password at https://my.abode.com

### "Unable to Connect"

**Cause:** Network connectivity issue

**Solutions:**
- Verify internet connection
- Check firewall/proxy settings
- Verify DNS resolution
- Try from different network
- Check Abode API status

### "Request Timeout"

**Cause:** API response too slow

**Solutions:**
- Check network latency
- Increase polling interval
- Increase retry count
- Check Home Assistant resources

### "Service Unavailable"

**Cause:** Abode API temporarily down

**Solutions:**
- Check https://status.goabode.com/
- Wait for service to recover
- Reload integration when service returns
- Check Home Assistant logs

### "Invalid Device"

**Cause:** Device not recognized by jaraco.abode library

**Solutions:**
- Verify device is supported
- Check Abode app for device type
- Update integration to latest version
- Report to GitHub issues

## Collecting Logs

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.abode_security: debug
    jaraco.abode: debug
```

Then:
1. Restart Home Assistant
2. Reproduce the issue
3. Collect logs from Settings → System → Logs

### Export Full Logs

```bash
# SSH into Home Assistant
# View logs
docker logs homeassistant | grep abode_security

# Or for standalone
tail -f ~/.homeassistant/home-assistant.log | grep abode_security
```

### Collecting Diagnostics

1. Settings → Devices & Services → Abode Security
2. Click three-dot menu
3. Click Download Diagnostics
4. Share the file (remove sensitive data)

## Using Diagnostics

### Interpreting Diagnostic Output

**Connection Status:**
- `Connected: true` - Integration is connected
- `Last update: recent` - Updates are working

**Device Information:**
- `Device count: N` - Number of devices
- `Device types: [...]` - Supported types found

**Configuration:**
- `Polling enabled: true/false`
- `Polling interval: N seconds`
- `Events enabled: true/false`

**Error Information:**
- `Last error: ...` - Most recent error
- `Error count: N` - Total errors
- `Error type: ...` - Type of error

### Example Analysis

```json
{
  "connection_status": "connected",
  "device_count": 5,
  "device_types": ["binary_sensor", "switch", "lock"],
  "polling_enabled": true,
  "polling_interval": 30,
  "last_update": "2 seconds ago",
  "last_error": null
}
```

**Interpretation:**
- ✅ Integration is healthy
- ✅ Devices are discoverable
- ✅ Polling is working normally

## Getting Help

### Before Posting for Help

1. ✅ Read this guide
2. ✅ Check Home Assistant logs
3. ✅ Download diagnostics
4. ✅ Verify credentials
5. ✅ Try reloading/restarting

### Where to Get Help

1. **GitHub Issues**
   - https://github.com/molant/abode-security/issues
   - Include diagnostic file
   - Include Home Assistant version
   - Include integration version
   - Include error messages

2. **Home Assistant Forums**
   - https://community.home-assistant.io/
   - Search for existing discussions
   - Include diagnostic information

3. **Home Assistant Discord**
   - https://discord.gg/home-assistant
   - Search in #custom-integrations
   - Provide diagnostic details

### Information to Include

When reporting issues, provide:
- Home Assistant version
- Integration version
- Integration installation method (HACS/manual)
- Home Assistant OS (Raspberry Pi, Docker, Standalone, etc.)
- Diagnostic file (anonymized)
- Relevant log entries
- Steps to reproduce
- Expected vs actual behavior

## FAQ

### Q: Why is my integration disconnecting?

**A:** Check network connectivity, firewall rules, and retry count. Increase polling interval if high frequency causes issues.

### Q: Why aren't my devices showing?

**A:** Verify devices are assigned in Abode account, check device is online, try reloading the integration.

### Q: Why are updates slow?

**A:** Try decreasing polling interval, enable events, check network latency, verify Home Assistant resources.

### Q: Does this support 2FA?

**A:** No, 2FA is not currently supported. Disable 2FA on your Abode account to use this integration.

### Q: Can I use multiple integrations?

**A:** Yes, you can add the integration multiple times for different Abode accounts (though single instance is typical).

### Q: What's the minimum Home Assistant version?

**A:** Version 2024.1.0 or later is required.

### Q: Is this officially supported?

**A:** This is a community integration, not officially supported by Home Assistant or Abode. Support is provided via GitHub issues.

### Q: How do I contribute fixes?

**A:** See [DEVELOPMENT.md](DEVELOPMENT.md) for contributing guidelines.

### Q: Where do I report security issues?

**A:** Do NOT create public GitHub issues for security vulnerabilities. Contact maintainer privately via GitHub.

---

**Back to:** [README.md](README.md)
