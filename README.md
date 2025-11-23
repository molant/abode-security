# Abode Security - Home Assistant Custom Integration

A custom HACS integration for the Abode Security System, providing full control over features, improvements, and release cycles.

## Features

- **Alarm Control Panel** - Monitor and control your Abode security system
- **Manual Alarm Trigger** - Manually trigger alarms with dedicated service calls
- **Test Mode** - Enable test mode to prevent dispatch notifications
- **Multiple Platforms**
  - Binary Sensors (door/window, motion detection)
  - Cameras (video feeds)
  - Covers (doors/windows)
  - Lights (smart lights)
  - Locks (smart locks)
  - Sensors (temperature, humidity, etc.)
  - Switches (control switches + test mode toggle)
  - Alarm Control Panel (main security control)

## Installation

### Via HACS

1. Click on HACS in the Home Assistant sidebar
2. Click on "Integrations"
3. Click the "+" icon
4. Search for "Abode Security"
5. Click "Install"
6. Restart Home Assistant

### Manual Installation

1. Clone or download this repository
2. Copy the `abode_security` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Configuration

After installing the integration:

1. Go to Settings → Devices & Services → Integrations
2. Click "Create Integration"
3. Search for "Abode Security"
4. Enter your Abode username and password
5. Choose whether to enable polling (optional)
6. Complete the setup

## Available Services

### Trigger Alarm
```yaml
service: abode_security.trigger_alarm
data:
  code: "your_alarm_code"
```

### Acknowledge Alarm
```yaml
service: abode_security.acknowledge_alarm
```

### Dismiss Alarm
```yaml
service: abode_security.dismiss_alarm
```

### Enable Test Mode
```yaml
service: abode_security.enable_test_mode
```

### Disable Test Mode
```yaml
service: abode_security.disable_test_mode
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development notes, architecture decisions, and planned improvements.

## License

This integration is based on the official Home Assistant Abode integration. See original component documentation for license information.

## Support

For issues, feature requests, or questions:
- Check [DEVELOPMENT.md](DEVELOPMENT.md) for known issues
- Open an issue on GitHub
- Check Home Assistant community forums

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request
