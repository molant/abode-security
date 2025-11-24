# Configuration Guide - Abode Security Integration

Comprehensive guide to configuring the Abode Security integration for Home Assistant.

## Table of Contents

- [Initial Configuration](#initial-configuration)
- [Configuration Options](#configuration-options)
- [Advanced Configuration](#advanced-configuration)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Initial Configuration

After installing the integration, follow these steps to configure it:

### 1. Add the Integration

- Go to **Settings** → **Devices & Services** → **Create Integration**
- Search for "Abode Security"
- Click the integration card

### 2. Enter Credentials

You'll be prompted for:
- **Email**: Your Abode account email address
- **Password**: Your Abode account password
- **Enable Polling**: Whether to poll for updates (recommended: enabled)

### 3. Complete Setup

- Click **Create** to add the integration
- Home Assistant will initialize the integration and create entities
- Devices should appear within a few seconds

## Configuration Options

After initial setup, you can customize the integration behavior.

### Accessing Configuration Options

1. Go to **Settings** → **Devices & Services** → **Abode Security**
2. Click **Options** (gear icon)
3. Modify settings as needed
4. Click **Submit**

### Available Options

#### Polling Interval

**Description:** How often Home Assistant queries the Abode API for updates (in seconds)

**Default:** 30 seconds

**Valid Range:** 15-120 seconds

**Recommendations:**
- **15-30 seconds**: Real-time updates, higher API load
- **30-60 seconds**: Balanced approach (recommended)
- **60-120 seconds**: Lower API load, delayed updates

**Example:**
```
Polling Interval: 45
```

#### Enable Events

**Description:** Use event-based updates instead of polling when available

**Default:** True (enabled)

**Options:**
- **True**: Use events for faster updates when available
- **False**: Use polling only

**Recommendations:**
- Keep enabled for the best experience
- Disable if experiencing event-related issues

**Example:**
```
Enable Events: True
```

#### Retry Count

**Description:** Number of times to retry failed API requests

**Default:** 3

**Valid Range:** 1-5 retries

**Recommendations:**
- **1-2**: Minimal retries, faster failures
- **3**: Balanced approach (recommended)
- **4-5**: Maximum resilience, slower on failures

**Example:**
```
Retry Count: 3
```

## Advanced Configuration

### Customizing per Device

Individual devices can be customized through Home Assistant's entity editor:

1. Go to **Settings** → **Devices & Services** → **Entities**
2. Search for your Abode device
3. Click the entity
4. Configure as needed:
   - Change name
   - Assign to areas/zones
   - Customize icon
   - Hide from UI
   - etc.

### Automation with Abode Services

Create automations using Abode Security services:

```yaml
automation:
  - alias: "Arm on Night"
    trigger:
      platform: time
      at: "23:00:00"
    action:
      service: alarm_control_panel.alarm_arm_away
      target:
        entity_id: alarm_control_panel.abode_security
```

### Using Triggers

Create automations based on Abode events:

```yaml
automation:
  - alias: "Door Sensor Triggered"
    trigger:
      platform: state
      entity_id: binary_sensor.front_door
      to: "on"
    action:
      service: notify.send_notification
      data:
        message: "Front door opened"
```

### Service-Based Automations

Use Abode-specific services:

```yaml
automation:
  - alias: "Trigger Manual Alarm"
    trigger:
      platform: homeassistant
      event: homeassistant_start
    action:
      service: abode_security.trigger_alarm
      data:
        alarm_type: "panic"
```

## Examples

### Example 1: Basic Setup with Custom Polling

Configuration:
- Polling Interval: 60 seconds
- Enable Events: True
- Retry Count: 3

**Result:** Moderate update frequency with event fallback for faster response

### Example 2: Real-Time Monitoring

Configuration:
- Polling Interval: 15 seconds
- Enable Events: True
- Retry Count: 5

**Result:** Quick updates with maximum reliability

**Use case:** Security monitoring or if you need instant notifications

### Example 3: Low Load Configuration

Configuration:
- Polling Interval: 120 seconds
- Enable Events: False
- Retry Count: 1

**Result:** Minimal API load

**Use case:** Limited bandwidth or shared API quotas

### Example 4: Automation with Multiple Conditions

```yaml
automation:
  - alias: "Security Alert"
    trigger:
      - platform: state
        entity_id: alarm_control_panel.abode_security
        to: "armed_away"
      - platform: state
        entity_id: binary_sensor.motion_sensor_1
        to: "on"
    condition:
      condition: and
      conditions:
        - condition: state
          entity_id: alarm_control_panel.abode_security
          state: "armed_away"
        - condition: state
          entity_id: binary_sensor.motion_sensor_1
          state: "on"
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Security Alert"
          message: "Motion detected while armed away"
      - service: abode_security.acknowledge_timeline_event
        data:
          event_id: "{{ trigger.event_id }}"
```

## Best Practices

### 1. Polling Interval Selection

- Start with 30 seconds (default)
- Increase if you see API rate limit warnings
- Decrease if you need faster updates
- Monitor Home Assistant logs for rate limiting

### 2. Error Handling

- Set Retry Count to at least 2 for reliability
- Monitor diagnostics for API errors
- Check network connectivity regularly
- Verify Abode account status

### 3. Performance Optimization

- Disable unused entity types in individual entity settings
- Use event-based updates when possible
- Avoid excessive automations
- Monitor Home Assistant memory usage

### 4. Security Recommendations

- Store passwords in Home Assistant Secrets:
  ```yaml
  # In your automation:
  service: abode_security.some_service
  data:
    password: !secret abode_password
  ```

- Use strong passwords for Abode account
- Enable 2FA on Abode account when available
- Restrict Home Assistant access with authentication

### 5. Backup and Recovery

- Export your Home Assistant configuration
- Keep documentation of your automations
- Test automations in a safe environment first
- Have manual alarm control as backup

## Troubleshooting

### Options Not Saving

**Problem:** Configuration changes don't persist after restart.

**Solutions:**
1. Verify you clicked **Submit**
2. Check Home Assistant logs for errors
3. Restart the integration:
   - Go to **Settings** → **Devices & Services** → **Abode Security**
   - Click the three-dot menu
   - Click **Reload**

### Polling Too Frequent

**Problem:** Integration is making too many API requests.

**Solutions:**
1. Increase polling interval:
   - Go to **Options**
   - Increase "Polling Interval" value
   - Click **Submit**
2. Check for excessive automations
3. Monitor API usage in Abode account

### Polling Not Frequent Enough

**Problem:** Updates are too slow.

**Solutions:**
1. Decrease polling interval:
   - Go to **Options**
   - Decrease "Polling Interval" value
   - Click **Submit**
2. Enable events:
   - Go to **Options**
   - Set "Enable Events" to True
   - Click **Submit**
3. Check network connectivity

### Some Entities Not Updating

**Problem:** Specific devices not updating their state.

**Solutions:**
1. Check device online status in Abode app
2. Verify device isn't temporarily unavailable
3. Reload the integration
4. Download diagnostics to check device status
5. Try removing and re-adding the device

### Configuration Reset

If you need to reset to factory configuration:

1. Go to **Settings** → **Devices & Services** → **Abode Security**
2. Click the three-dot menu
3. Click **Delete** to remove the integration
4. Restart Home Assistant
5. Re-add the integration with default options

## Related Documentation

- [README.md](README.md) - Main documentation
- [INSTALLATION.md](INSTALLATION.md) - Installation instructions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
- [DEVELOPMENT.md](DEVELOPMENT.md) - Development information

---

**Back to:** [README.md](README.md)
