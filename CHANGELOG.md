# Changelog - Abode Security Integration

All notable changes to the Abode Security integration are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v1.1.0 (2026-05-23)

### Features
-  list all HA cameras + render via ha-camera-stream
-  deep-link tap-to-camera via /abode_security panel
-  add Cameras tab + deep-link routing (Sub-Phase B)
-  add abode_security/entities/cameras WS endpoint (Sub-Phase A)
-  tap → camera live view via clickAction
-  copy-action-ID button + docs polish
-  allow notification-only actions (no alarm)
-  add debug fire_test_notification service
-  add docs, blueprint, README pointer, and action_trigger snapshot wiring
-  wire daily snapshot purge + retention option in config flow
-  add async_purge_old to snapshot.py with executor-offloaded I/O
-  wire snapshot capture into action trigger
-  add snapshot.py with camera discovery and capture helpers
-  enrich action_triggered payload with sensor context
-  add _SensorTriggerContext and thread through trigger chain
-  single-select alarm picker with responsive grid layout
-  table-align sensor rows; drop red separator and lifetime counter chip
-  surface sensor availability + state in picker and actions list
-  collapse sensor categories and add search (#113)
-  record device audit result, no deletes (phase 4D)
-  add structured DEBUG log per connect attempt (phase 4C)
-  surface SocketIO health counters in diagnostics.py (phase 4B)
-  add SocketIO health counter properties (phase 4A)
-  remove lomond from manifest/deps, update UPSTREAM.md (phase 3C+3D)
-  drop run_coroutine_threadsafe bridge in EventController (phase 3B)
-  rewrite SocketIO as fully async (phase 3A)
-  add async WebSocket transport scaffold (phase 2)
-  implement phase 1 fork hygiene and audit log
-  admin-gate sensitive read-only websocket commands
-  enable mypy strict for outer integration (fixes #56)
-  mode-switching UI from Modes tab (fixes #1)
-  a11y focus management + document Escape on <abode-modal> (fixes #9, #28)
-  Add GitHub release scripts for HACS integration
-  Add complete dashboard UI with actions and modes tabs
-  Add ActionTriggerCoordinator for sensor-based action triggering
-  Add config endpoints and integration setup
-  Add entity query endpoints for modes, sensors, alarms
-  Add WebSocket API for action CRUD operations
-  Add ActionManager helper methods
-  Add ActionManager with CRUD operations and validation
-  Add ActionStore for persistent action storage
-  Add AbodeAction dataclass with serialization
-  Add Playwright E2E testing and fix panel registration (Phase 5 & 6)
-  Add frontend build infrastructure (Phase 5)
-  Add Claude Code skills and pre-commit review hook
-  Enable CMS Settings Switch tests (Phase 4.5.3)
-  Enable switch platform tests (Phase 4.5.3)
-  Enable camera platform tests (Phase 4.5.3)
-  Enable alarm control panel integration tests (Phase 4.5.3)
-  Enable light platform tests (Phase 4.5.3)
-  Enable sensor platform tests (Phase 4.5.3)
-  Enable lock platform tests (Phase 4.5.3)
-  Enable cover platform tests (Phase 4.5.3)
-  Complete binary_sensor platform tests (Phase 4.5.3)
-  Enable init tests (Phase 4.5.2)
-  Enable config flow tests (Phase 4.5.1)
-  Complete Phase 4 test infrastructure for mock server
-  Add test infrastructure for mock server integration
-  Add WebSocket/SocketIO support to mock server
-  Add configurable base URL for Abode API
-  Add FastAPI mock Abode API server
-  Add Docker development environment
-  Add debug logging configuration and improve options UI
-  Optimize CMS settings caching and API efficiency
-  Add CMS configuration switches for Abode security settings
-  Add Abode integration icon
-  Add Batch Operations to async wrapper (Phase 4B)
-  Add Event Filtering system (Phase 4B)
-  Add Smart Polling and Configuration Presets (Phase 4B)
-  Implement options flow for user configuration (Phase 4B)
-  Enhance manifest, hacs config, and README (Phase 4A)
-  Enhance diagnostics with comprehensive system information (Phase 3E)
-  Create async wrapper for jaraco.abode operations (Phase 3D)
-  Add user-configurable settings framework (Phase 3C)
-  Add comprehensive type hint coverage (Phase 3B)
-  Add error handling decorators to switch methods (Phase 3A)

### Fixes
-  address PR #139 review feedback + starlette CVE
-  set both `url` and `clickAction` for tap-to-camera
-  address PR review feedback
-  address PR #137 review feedback and bump idna for CVE-2026-45409
-  exclude entities hidden in the entity registry from the sensor picker
-  polish action editor and modes UI (#120)
-  rename dispatch handlers to match protocol verbs
-  move integration icon to brand/ folder for HA 2026.3+
-  address PR #112 review feedback
-  track in-flight refresh futures + pin mock to EIO v3
-  async_create accepts enabled kwarg
-  align WS validation error code with runtime path
-  null-check Alarm before constructing alarm-attached entities
-  null-check get_alarm() before trigger_manual_alarm
-  use public HA import paths
-  bound websocket command payload sizes (fixes #55)
-  re-check alarm mode in _delayed_execute (fixes #53)
-  tolerate corrupt records on action-store load (fixes #54)
-  correct override() annotation in vendored config (fixes #57)
-  redact PII from diagnostics output (fixes #50)
-  redact tokens and PII from DEBUG response logs (fixes #49)
-  resolve Abode alarm panel via entity registry (fixes #44)
-  singular "action" for count of 1 in modes badge (fixes #24)
-  lifecycle + async safety for editor and tabs (fixes #10, #26, #27, #29)
-  drive editor sensor categories from response keys (fixes #25)
-  drain in-flight requests in cleanup() (fixes #14)
-  cleanup() Abode client on every login attempt (fixes #6)
-  document single-entry contract for hass.data writes
-  preserve entry on reauth, abort on username change
-  serialize session recreate, drain in-flight requests (fixes #3)
-  refresh cookies on reconnect; surface persistent disconnect
-  correctness fixes for retries, session guards, and shutdown
-  prevent spurious alarm triggers and double-fire on re-trigger
-  unwrap WebSocket responses correctly
-  Handle undefined state during initial render
-  Correct WebSocket endpoint types and modes response format
-  Use thread-safe add_job() for automation trigger callback
-  Update test constants to match actual entity IDs (Phase 4.5.3)
-  Immediately recreate session on CMS endpoint empty response
-  Clear CMS cache on session recreation to ensure fresh fetch
-  Add background session monitor to prevent timeout with SocketIO events
-  Improve SocketIO authentication and connection reliability
-  Resolve integration icon display by using local icon file
-  Use upstream Abode icon from Home Assistant brands repository
-  Code quality improvements (Phase 4A - Validation)

### Other Changes
- docs+test: address Copilot feedback on modes/list and mutating-command coverage
- Pre-release: 20260119-2140
- remove unnecessary docs
- fix init flow for HACS
- update readme.md
- Implement hybrid dependency approach for jaraco utilities
- Phase 5: Convert HTTP client from requests to aiohttp (async) + bug fixes
- Fix import ordering across all test files
- Add comprehensive end-to-end test scenarios
- Add comprehensive integration tests for advanced features
- Improve test mode initialization and polling with better logging
- Initial setup: Create abode-security custom HACS integration

## v1.2.0 (2026-05-28)

### Features
-  use mdi icons for schedule row edit/delete buttons
-  rebuild frontend bundle with schedules UI
-  Phase 4F – Playwright E2E happy-path test for scheduled arming
-  Phase 4E – mount schedules section in modes-tab
-  Phase 4D – schedules-section list container with CRUD and admin gating
-  Phase 4C – schedule-row inline-edit component
-  Phase 4B – day-chip-picker weekday selector component
-  Phase 4A – types and API client wrappers for schedules
-  Phase 3G – integration test for arm/disarm cycle
-  Phase 3A-F – runtime arm/disarm, retry, reconcile, listener, events
-  Phase 2C – ModeChanger protocol and HAModeChanger impl
-  Phase 2B – ScheduleClock protocol and HAScheduleClock impl
-  Phase 2A – Clock protocol and HAClock impl
-  Phase 1 – domain models, storage, CRUD, WS endpoints

### Fixes
-  live-reactive active mode + cancel mid-arming (fixes #124)
-  surface disabled actions in mode card (fixes #123)
-  expose camera smart-detect categories in sensor picker (fixes #135)

## v1.2.1 (2026-05-29)

### Fixes
-  disarm never fires due to derive_state boundary

## v1.2.2 (2026-06-11)

### Fixes
-  bump pip 26.1.1 -> 26.1.2 to clear PYSEC-2026-196
-  stop pinning logger level so logger.set_level works
-  add dark-mode icon variant (fixes #153)

## v1.2.3 (2026-08-28)

### Fixes
-  stop skipped arms stamping last_disarmed_at (fixes #213)
-  adopt a manually-armed panel mid-window (fixes #212)
-  give uv.lock an automated bump path (fixes #218)
-  keep waiting for a late panel after HA start
-  ignore panel unavailability in the override listener
-  stop offline sensors reading as clear (fixes #210)
-  keep the runtime up when platform unload fails
-  merge runtime fields instead of writing back a stale pair
-  quiesce in-flight schedule work at teardown
-  move the alarm timeline lookup off the trigger path
-  reject untriggerable alarm targets at write time
-  confirm panel state before calling a schedule failed
-  stop offering alarm types Abode rejects, and surface failures

## [1.0.0] - 2024-11-23

### ✨ Initial Release

This is the first public release of the Abode Security integration for Home Assistant.

### 🎯 Features

#### Core Functionality
- **Alarm Control Panel** - Full control over Abode security system
  - Arm/disarm operations
  - Home mode and away mode
  - Status monitoring with state tracking
  - Battery level monitoring

- **Manual Alarm Trigger** - Trigger alarms with event tracking
  - Support for panic, fire, and police alarm types
  - Event timeline integration
  - Automatic event dismissal

- **Test Mode** - Enable/disable test mode
  - Prevent dispatch notifications
  - Useful for system testing and configuration
  - Easy toggle via switch entity

#### Platform Support
- **Binary Sensors** (door/window, motion, connectivity)
- **Cameras** (video feeds, capture, privacy mode)
- **Covers** (doors, blinds, garage doors)
- **Lights** (brightness, color, effects)
- **Locks** (lock/unlock control)
- **Sensors** (temperature, humidity, light level)
- **Switches** (device control, automation toggling)

#### Services
- `trigger_alarm` - Trigger manual alarms
- `acknowledge_timeline_event` - Acknowledge security events
- `dismiss_timeline_event` - Dismiss security events
- `trigger_automation` - Trigger Abode automations
- `enable_test_mode` - Enable test mode
- `disable_test_mode` - Disable test mode

#### Configuration
- User-configurable polling intervals (15-120 seconds)
- Event-based update support (when available)
- Configurable retry count (1-5)
- Persistent configuration storage

#### Code Quality
- **Full Type Hints** - 95%+ type coverage
  - IDE support and autocomplete
  - mypy type checking compatibility

- **Error Handling** - Comprehensive error handling
  - Decorators on all device operations
  - Graceful degradation on failures
  - Clear error logging

- **Async Foundation** - 8+ async wrapper methods
  - Non-blocking operations
  - Future-ready architecture

- **Enhanced Diagnostics** - 15+ diagnostic fields
  - Connection status
  - Device inventory
  - System capabilities
  - Error information

### 📋 Configuration

- HACS support with automatic installation
- Manifest.json with proper metadata
- hacs.json with documentation links
- Config flow for initial setup
- Options flow for configuration changes

### 📚 Documentation

- **README.md** - Main documentation with features and quick start
- **INSTALLATION.md** - Step-by-step installation instructions
- **CONFIGURATION.md** - Detailed configuration guide
- **TROUBLESHOOTING.md** - Comprehensive troubleshooting guide
- **CHANGELOG.md** - This file with version history
- **DEVELOPMENT.md** - Development setup and architecture

### 🧪 Testing

- Unit tests for error handling
- Integration tests for entity lifecycle
- Service call testing
- Configuration validation testing

### 🔒 Security

- No hardcoded secrets or credentials
- Credential validation in config flow
- Secure password handling
- No sensitive data in logs

### 📦 Dependencies

- `jaraco.abode==6.2.1` - Abode API client

### 🎯 System Requirements

- Home Assistant 2024.1.0 or later
- Python 3.9 or later
- Network access to Abode API
- Abode account with assigned devices

### ✅ Pre-Release Checks

- ✅ All ruff linting checks pass
- ✅ Full type hint coverage
- ✅ Comprehensive error handling
- ✅ Unit and integration tests
- ✅ No hardcoded secrets
- ✅ Documentation complete
- ✅ HACS requirements met

### 🚀 Known Limitations

1. **No 2FA Support** - Two-factor authentication not supported
2. **Sync API Only** - jaraco.abode library is synchronous
3. **Limited Features** - Some advanced Abode features not available

### 📝 Notes

This release represents the completion of Phase 3 development and is ready for public release via HACS.

The integration provides a solid foundation with room for future enhancements including:
- Native async support when jaraco.abode supports it
- Smart polling optimization
- Configuration presets
- Event filtering
- Batch operations
- Multi-language support
- Advanced analytics and history

---

## Future Releases

### [1.1.0] - Planned

**Smart Polling**
- Adaptive polling based on activity
- Automatic interval optimization
- Load-based adjustments

**Configuration Presets**
- Quick setup profiles
- User-defined presets
- One-click configuration

**Event Filtering**
- Select which events trigger updates
- Reduce unnecessary polling
- Better performance

### [2.0.0] - Planned (requires jaraco.abode async support)

**Native Async Support**
- Full async/await implementation
- Eliminate executor job wrappers
- Better performance

**Advanced Features**
- Timeline analytics
- Event history
- Usage patterns
- Performance metrics

---

## Version History Summary

| Version | Date | Status | Focus |
|---------|------|--------|-------|
| 1.0.0 | 2024-11-23 | ✅ Released | Initial public release |
| 0.1.0 | 2024-11-xx | Internal | Initial development |

---

## Migration Guides

### From Official Home Assistant Abode Integration

If you were using the official Home Assistant Abode integration, migration is simple:

1. **Backup your current configuration**
2. **Remove the official integration**
3. **Install Abode Security from HACS**
4. **Re-add the integration with your credentials**
5. **Update any automations if needed**

All entity IDs remain the same, so automations and scripts should continue working.

### Breaking Changes in Future Releases

None in 1.0.0. We're committed to backward compatibility.

---

## Contributing

Found a bug or want to contribute? See [development.md](development.md) for:
- Issue reporting guidelines
- Pull request process
- Code standards
- Testing requirements

---

## Credits

- **Original Concept** - Based on Home Assistant's official Abode integration
- **jaraco.abode** - Python client library for Abode API
- **Home Assistant** - Automation platform
- **Community** - Testers and contributors

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

**Last Updated:** 2024-11-23

**For more information:**
- [README.md](README.md) - Main documentation
- [INSTALLATION.md](INSTALLATION.md) - Installation guide
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
- [GitHub Issues](https://github.com/molant/abode-security/issues) - Report bugs or request features
