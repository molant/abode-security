# Abode Security - Home Assistant Custom Integration

A powerful Home Assistant integration for the Abode Security System, providing real-time control and monitoring of your security system with full type safety, comprehensive error handling, and extensive diagnostics.

[![GitHub Release](https://img.shields.io/github/v/release/molant/abode-security?label=Version)](https://github.com/molant/abode-security/releases)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-blue.svg)](https://github.com/home-assistant/core/releases/tag/2024.1.0)

## Features

### Core Capabilities
- **Alarm Control Panel** - Full control over your Abode security system (arm, disarm, home mode, away mode)
- **Manual Alarm Trigger** - Trigger alarms with optional event dismissal support
- **Test Mode** - Enable test mode to prevent dispatch notifications during testing
- **Event Timeline** - Access to security events with acknowledge/dismiss capabilities
- **Real-time Polling** - Configurable polling intervals (15-120 seconds) with event-based fallback

### Supported Platforms
- **Binary Sensors** - Motion detection, door/window sensors, connectivity status
- **Cameras** - Video feeds with capture and privacy mode control
- **Covers** - Automated doors, blinds, and garage door control
- **Lights** - Smart light control with brightness and color support
- **Locks** - Smart lock control (lock/unlock)
- **Sensors** - Temperature, humidity, light level, and custom sensors
- **Switches** - Individual device control and automation enable/disable
- **Alarm Control Panel** - Main security system control and status

### Advanced Features
- **Full Async Support** - Built-in async/await patterns throughout the integration
- **Async HTTP Client** - aiohttp-based client for non-blocking network operations
- **Event Filtering** - Advanced event filtering system for timeline management
- **Batch Operations** - Efficient batch processing for device operations
- **Smart Polling** - Intelligent polling with configuration presets and event-based fallback
- **Comprehensive Error Handling** - Graceful degradation on API failures
- **Enhanced Diagnostics** - Detailed system information for troubleshooting
- **User Configuration Framework** - Customizable polling and event settings
- **Type Safety** - Full type hints for IDE support and mypy compatibility

## Quick Start

### Installation via HACS

1. Open Home Assistant and go to **Settings** → **Devices & Services** → **HACS**
2. Click the **+** button in the bottom right
3. Search for "Abode Security"
4. Click **Download**
5. Restart Home Assistant
6. Go to **Settings** → **Devices & Services** → **Create Integration**
7. Search for "Abode Security" and follow the setup wizard

### Manual Installation

1. Clone this repository or download the latest release:
   ```bash
   git clone https://github.com/molant/abode-security.git
   ```

2. Copy the `custom_components/abode_security` folder to your Home Assistant `custom_components` directory:
   ```bash
   cp -r custom_components/abode_security ~/.homeassistant/custom_components/
   ```

3. Restart Home Assistant

4. Configure the integration:
   - Go to **Settings** → **Devices & Services** → **Create Integration**
   - Search for "Abode Security"
   - Enter your Abode credentials and configure options

## Configuration

### Initial Setup

During integration setup, you'll be prompted for:
- **Abode Email** - Your Abode account email
- **Abode Password** - Your Abode account password
- **Enable Polling** - Whether to poll the Abode API for updates (default: True)

### Configuration Options

After setup, configure advanced options in Home Assistant:
- **Polling Interval** (15-120 seconds, default: 30) - How often to check for updates
- **Enable Events** (True/False, default: True) - Use event-based updates when available
- **Retry Count** (1-5, default: 3) - Number of retries for failed API calls

See [CONFIGURATION.md](CONFIGURATION.md) for detailed configuration options and tuning guides.

## Available Services

### Trigger Alarm
Trigger a manual alarm with optional event tracking.

```yaml
service: abode_security.trigger_alarm
data:
  alarm_type: "panic"  # or "fire", "police"
```

### Acknowledge Timeline Event
Acknowledge a security event in the timeline.

```yaml
service: abode_security.acknowledge_timeline_event
data:
  event_id: "event_123456"
```

### Dismiss Timeline Event
Dismiss a security event.

```yaml
service: abode_security.dismiss_timeline_event
data:
  event_id: "event_123456"
```

### Trigger Automation
Trigger an Abode automation.

```yaml
service: abode_security.trigger_automation
data:
  automation_id: "automation_123"
```

### Enable Test Mode
Prevent dispatch notifications during system testing.

```yaml
service: abode_security.enable_test_mode
```

### Disable Test Mode
Re-enable dispatch notifications.

```yaml
service: abode_security.disable_test_mode
```

## Troubleshooting

### Common Issues

**Integration not appearing after installation:**
- Check that `manifest.json` has the correct `domain: abode_security`
- Ensure ruff linting passes: `python3 -m ruff check custom_components/abode_security/`
- Restart Home Assistant completely

**Devices not appearing:**
- Check the Home Assistant logs for errors
- Verify your Abode credentials are correct
- Check that your Abode account has devices assigned

**Slow responses:**
- Check current polling interval in integration options
- Consider increasing polling interval if API is slow
- Check Home Assistant system resources

**Authentication errors:**
- Verify your Abode password is correct
- Check if your Abode account has 2FA enabled (currently not supported)
- Try re-authenticating the integration

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more detailed troubleshooting steps and diagnostic information.

## Diagnostics

The integration includes comprehensive diagnostics that can help troubleshoot issues:

1. Go to **Settings** → **Devices & Services** → **Abode Security**
2. Click the three-dot menu
3. Select **Download diagnostics**

The diagnostic file includes:
- Connection status and configuration
- Device inventory and types
- Automation status
- System capabilities
- Error information (if any)

## Performance

### Typical Performance Metrics
- **Entity creation:** < 2 seconds
- **Polling response time:** < 2 seconds
- **Configuration change:** < 5 seconds
- **Diagnostics collection:** < 2 seconds
- **Memory usage:** ~50-100 MB typical

### Optimization Tips
1. Adjust polling interval based on your needs
   - More frequent (15-30s): Real-time updates but higher API load
   - Less frequent (60-120s): Lower API load but delayed updates
2. Enable event-based updates to reduce polling load
3. Review diagnostics regularly to identify issues early

## Development

This integration includes:
- **Full Type Hints** - 95%+ type coverage for IDE support
- **Comprehensive Testing** - Unit and integration tests for all components
- **Clean Architecture** - Modular design for easy maintenance
- **Error Handling** - Consistent error handling with decorators
- **Async Foundation** - Foundation for non-blocking operations

See [DEVELOPMENT.md](DEVELOPMENT.md) for:
- Architecture overview
- Contributing guidelines
- Development setup
- Testing instructions
- Building and deployment

## Architecture & Implementation

### Async-First Design
The integration uses an async-first architecture with:
- **aiohttp-based HTTP client** - Async network requests for non-blocking I/O
- **Async service handlers** - All I/O operations properly awaited
- **Event loop integration** - Full Home Assistant async patterns compliance
- **Hybrid dependency approach** - Minimal external dependencies with inline utilities

For detailed information on async patterns, see [ASYNC_AWAIT_PATTERNS.md](docs/ASYNC_AWAIT_PATTERNS.md).

## Known Limitations

1. **No 2FA Support** - Two-factor authentication not currently supported
2. **Limited Features** - Some advanced Abode features not exposed by the underlying library

## Support & Contributing

### Getting Help
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Review [Integration Diagnostics](#diagnostics) for system information
- [Open an issue](https://github.com/molant/abode-security/issues) with details about your problem
- Check [Home Assistant Community Forums](https://community.home-assistant.io/)

### Contributing
Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with clear commit messages
4. Add or update tests as needed
5. Ensure all checks pass (ruff, type hints, tests)
6. Submit a pull request

See [DEVELOPMENT.md](DEVELOPMENT.md#contributing) for more detailed contribution guidelines.

## Acknowledgments

This integration builds upon:
- **[jaraco.abode](https://github.com/jaraco/abode)** - The underlying Abode Python client library, maintained by the jaraco community
- **[Home Assistant](https://github.com/home-assistant/core)** - The amazing open-source home automation platform

Special thanks to the original Home Assistant Abode integration for inspiration. This custom integration is independently maintained with enhanced async support, improved code quality, comprehensive error handling, and extensive type safety.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

## Version History

### Latest Features
- **Async HTTP Client** - aiohttp-based client for non-blocking network operations (Phase 5)
- **Event Filtering** - Advanced timeline event filtering system (Phase 4B)
- **Batch Operations** - Efficient batch processing for device operations (Phase 4B)
- **Smart Polling** - Intelligent polling with configuration presets (Phase 4B)
- **User Configuration** - Customizable polling intervals and event settings (Phase 4A)
- **Hybrid Dependencies** - Reduced dependency complexity with inline utilities

### 1.0.0 (2024-11-23)
- **Initial Release**
- Full alarm system control and monitoring
- Support for 8 platforms (binary sensors, cameras, covers, lights, locks, sensors, switches, alarm control panel)
- Comprehensive error handling and type safety
- Enhanced diagnostics and user configuration
- Async foundation with full type hints

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and breaking changes.

## Related Projects

- [jaraco.abode](https://github.com/jaraco/abode) - Python Abode client library
- [Home Assistant](https://www.home-assistant.io/) - Open source home automation
- [Abode Security](https://goabode.com/) - Abode Security Systems

---

**Questions?** Check the [FAQ section](TROUBLESHOOTING.md#faq) or open an [issue](https://github.com/molant/abode-security/issues).

**Want to contribute?** See [DEVELOPMENT.md](DEVELOPMENT.md) for contribution guidelines.
