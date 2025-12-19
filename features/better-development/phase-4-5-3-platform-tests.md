# Phase 4.5.3: Enable Platform Tests

**Status**: ✅ Proof-of-Concept Complete
**Date**: 2025-12-18
**Prerequisites**: Phase 4.5.1 (Import Refactoring) ✅ Complete

## Goal

Enable platform tests (binary_sensor, alarm_control_panel, etc.) to validate entity creation and attributes.

## Current State

- **Tests to enable**: ~88 platform tests across 9 test files
- **Infrastructure**: Test framework complete (Phase 4)
- **Blocking issue**: Platform tests require real device objects, not just mocks

## Test Files

### Simple Platforms (Priority 1 - 10 tests)
- `test_binary_sensor.py` (2 tests) - Door/window sensors
- `test_cover.py` (4 tests) - Garage doors, shades
- `test_lock.py` (4 tests) - Smart locks

### Medium Platforms (Priority 2 - 13 tests)
- `test_sensor.py` (2 tests) - Temperature, humidity sensors
- `test_alarm_control_panel.py` (6 tests) - Main alarm panel
- `test_light.py` (7 tests) - Smart lights

### Complex Platforms (Priority 3 - 65 tests)
- `test_camera.py` (5 tests) - Security cameras
- `test_switch.py` (23 tests) - Various switches and automations
- `test_cms_settings_switches.py` (35 tests) - CMS monitoring settings

## Problem Analysis

### Issue: Mock Fixture Returns Empty Device List

Current `mock_abode` fixture in `tests/conftest.py`:
```python
@pytest.fixture
def mock_abode() -> Generator[Mock]:
    """Provide a mock Abode client."""
    mock_client = Mock()
    mock_client.get_devices = AsyncMock(return_value=[])  # ❌ Empty!
    mock_client._devices = []  # ❌ Empty!
    # ...
```

### What Platform Tests Need

Platform tests expect entities to be created from device data:

1. **Binary Sensor Test** (`tests/test_binary_sensor.py:31`):
   ```python
   entry = entity_registry.async_get("binary_sensor.front_door")
   assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"
   ```

2. **Device Creation Flow**:
   - Integration calls `abode.get_devices()`
   - Platform (`binary_sensor.py`) iterates over devices
   - Creates Home Assistant entities for each device
   - Registers entities with unique IDs

3. **Current Problem**:
   - `mock_abode.get_devices()` returns `[]`
   - No entities created
   - Tests fail with `AttributeError: 'NoneType' object has no attribute 'unique_id'`

## Solution Investigation

### Approach 1: Enhanced Mock Fixture (Attempted)

**Idea**: Update `mock_abode` to create real device objects from JSON fixtures.

**Implementation Attempt**:
```python
@pytest.fixture
def mock_abode() -> Generator[Mock]:
    """Provide a mock Abode client with real device objects."""
    from custom_components.abode_security.abode.devices.alarm import create_alarm
    from custom_components.abode_security.abode.devices.base import Device

    # Load device data from fixtures
    devices_json = json.loads(load_fixture("devices.json", "abode"))
    panel_json = json.loads(load_fixture("panel.json", "abode"))

    # Create real device objects
    devices_dict = {}
    for device_data in devices_json:
        device = Device.new(device_data, mock_client)
        devices_dict[device.id] = device

    # Mock get_devices to return real devices
    async def get_devices_mock(refresh=False, generic_type=None):
        # Filter by type if specified
        return [device for device in devices_dict.values()
                if generic_type is None or device.generic_type in generic_type]

    mock_client.get_devices = AsyncMock(side_effect=get_devices_mock)
    mock_client._devices = devices_dict
```

**Result**: Still failing - device creation has additional dependencies
- Devices may require network access during initialization
- Device methods may call Abode API endpoints
- Complex device state management

**Status**: ⚠️ Incomplete - needs more investigation

### Approach 2: Use Mock Server (Recommended)

**Idea**: Convert platform tests to integration tests using the mock HTTP server.

**Benefits**:
- Real device creation through actual HTTP responses
- Tests actual integration behavior, not mocked behavior
- Already have `mock_server` fixture (Phase 4)
- More realistic testing

**Implementation**:
```python
async def test_binary_sensor_with_mock_server(
    hass: HomeAssistant,
    mock_server_client,
    entity_registry: er.EntityRegistry
) -> None:
    """Test binary sensor using mock server."""
    # Set up config entry with mock server
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: mock_server_client["username"],
            CONF_PASSWORD: mock_server_client["password"],
        },
    )
    config_entry.add_to_hass(hass)

    # Let integration set up with real HTTP calls to mock server
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Now test that entities were created
    entry = entity_registry.async_get("binary_sensor.front_door")
    assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"
```

**Challenges**:
- Requires updating test structure
- May need to enhance mock server responses
- Different testing paradigm

**Status**: 🎯 Recommended approach for investigation

### Approach 3: Hybrid - Simple Mock + Selective Real Devices

**Idea**: Keep simple mock for most tests, create real devices only when needed.

**Implementation**:
- Add `mock_abode_with_devices` fixture for platform tests
- Keep simple `mock_abode` for init/config flow tests
- Investigate minimal device creation requirements

**Status**: 💡 Alternative if Approach 2 is too complex

## Key Learnings

### Device Creation Process

From `custom_components/abode_security/abode/client.py`:

1. **Fetch device data**:
   ```python
   response = await self.send_request("get", urls.DEVICES)
   devices_data = await response.json()
   ```

2. **Create device objects**:
   ```python
   for device_doc in devices:
       device = Device.new(device_doc, self)  # Creates typed device
       self._devices[device.id] = device
   ```

3. **Device types**:
   - `Device.new()` uses `type_tag` to determine device class
   - Returns `BinarySensor`, `Lock`, `Light`, `Camera`, etc.
   - Each has specific initialization requirements

### Fixture Data Available

- `tests/fixtures/devices.json` - Full device list (47 devices)
- `tests/fixtures/panel.json` - Alarm panel data
- `tests/fixtures/login.json` - Auth data
- `tests/fixtures/logout.json` - Logout response
- All fixtures from original jaraco.abode library

### Example Device (Front Door - Binary Sensor)

```json
{
  "id": "RF:01430030",
  "type_tag": "device_type.door_contact",
  "type": "Door Contact",
  "name": "Front Door",
  "uuid": "2834013428b6035fba7d4054aa7b25a3",
  "is_window": "1",
  "status_color": "#5cb85c",
  "faults": {
    "low_battery": 0,
    "tempered": 0
  }
}
```

## Investigation Results ✅ SUCCESSFUL (2025-12-18)

**Outcome**: Proof-of-concept test passing! Mock server approach validated.

### Research Questions - ANSWERED

- [x] Does mock server provide `/devices` endpoint? **YES** - tests/mock_server/main.py:252-257
- [x] Does mock server provide `/panel` endpoint? **YES** - tests/mock_server/main.py:161-171
- [x] Can we use mock server with Home Assistant test fixtures? **YES** - With configuration
- [x] What network calls do devices make during initialization? **None** - Devices created from API responses
- [x] Does mock server load fixtures correctly? **YES** - Loads 11 devices on startup

### Key Findings

1. **Mock Server Capabilities** ✅
   - Provides all necessary endpoints (`/api/v1/devices`, `/api/v1/panel`, etc.)
   - Loads device fixtures from `tests/fixtures/devices.json` (11 devices)
   - Missing `/health` endpoint - **ADDED** to support test fixture detection
   - Fully functional with real HTTP requests

2. **Integration Test Pattern** ✅
   - Use `@pytest.mark.integration` + `@pytest.mark.enable_socket` markers
   - Set `ABODE_BASE_URL` environment variable to mock server URL
   - **Critical**: Must reload `urls` module after setting env var (module-level import issue)
   - Create config entry with `CONF_POLLING: False` field
   - Let integration make real HTTP calls to mock server
   - Entities are created automatically with proper attributes

3. **Test Infrastructure** ✅
   - `mock_server` fixture (tests/conftest.py:178-228) manages server lifecycle
   - `mock_server_client` fixture provides test credentials and URL
   - `reset_mock_server` fixture ensures test isolation
   - Tests must be added to `enabled_tests` set in conftest.py to run

4. **Test Results** ✅
   ```
   ======================== 1 passed in 0.62s ========================
   Coverage:
   - binary_sensor.py: 100%
   - alarm_control_panel.py: 69%
   - camera.py: 54%
   - cover.py: 91%
   - lock.py: 91%
   - light.py: 77%
   - sensor.py: 89%
   - switch.py: 54%
   ```

### Implementation Changes

**1. Mock Server Enhancement** (tests/mock_server/main.py:404-407)
```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

**2. Binary Sensor Tests** (tests/test_binary_sensor.py)
- `test_binary_sensor_with_mock_server` - Entity registry validation
- `test_binary_sensor_attributes` - Entity attributes validation
- Key patterns demonstrated:
  - Import and reload urls module to pick up environment variable
  - Use `@pytest.mark.integration` and `@pytest.mark.enable_socket`
  - Include `CONF_POLLING` in config entry data
  - Restore environment in `finally` block
  - **IMPORTANT**: Use platform-specific test names (e.g., `test_binary_sensor_attributes` not just `test_attributes`) to avoid conflicts

**3. Test Configuration** (tests/conftest.py:43-44)
- Added both binary sensor tests to `enabled_tests` set

### Test Conversion Pattern

When converting platform tests to use mock server:

```python
@pytest.mark.integration
@pytest.mark.enable_socket
async def test_PLATFORM_SPECIFIC_NAME(
    hass: HomeAssistant,
    mock_server_client: dict[str, str]
) -> None:
    """Test description."""
    import importlib
    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)

    try:
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Your test assertions here

    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
```

**Critical Requirements:**
1. Test name must include platform prefix (e.g., `test_cover_attributes` not `test_attributes`)
2. Add test name to `enabled_tests` in conftest.py
3. Use both markers: `@pytest.mark.integration` and `@pytest.mark.enable_socket`
4. Always reload urls module after setting environment variable
5. Always restore environment in finally block

## Next Steps

### Immediate Actions

1. **Enable remaining binary_sensor test** - Convert test_attributes
2. **Document the pattern** - Add comments/docstring showing pattern for future tests
3. **Commit proof-of-concept** - Phase 4.5.3 milestone 1

### Rollout Plan

**Phase 1**: Simple Platforms (Priority 1 - 10 tests)
- [x] Binary sensor (2/2 tests) ✅ Complete - 2025-12-18
  - test_binary_sensor_with_mock_server ✅
  - test_binary_sensor_attributes ✅
- [x] Cover (4/4 tests) ✅ Complete - 2025-12-18 - 100% coverage
  - test_cover_entity_registry ✅
  - test_cover_attributes ✅
  - test_cover_open ✅
  - test_cover_close ✅
- [x] Lock (4/4 tests) ✅ Complete - 2025-12-18 - 100% coverage
  - test_lock_entity_registry ✅
  - test_lock_attributes ✅
  - test_lock_lock ✅
  - test_lock_unlock ✅

**Phase 2**: Medium Platforms (Priority 2 - 13 tests)
- [x] Sensor (2/2 tests) ✅ Complete - 2025-12-18 - 89% coverage
  - test_sensor_entity_registry ✅
  - test_sensor_attributes ✅
- [ ] Alarm control panel (6 tests)
- [ ] Light (7 tests)

**Phase 3**: Complex Platforms (Priority 3 - 65 tests)
- [ ] Camera (5 tests)
- [ ] Switch (23 tests)
- [ ] CMS settings switches (35 tests)

### Success Criteria

**Minimum**: Enable binary_sensor tests (2 tests)
- Validates basic platform setup works
- Proves the approach

**Good**: Enable simple platforms (10 tests)
- binary_sensor, cover, lock
- Covers basic entity types

**Excellent**: Enable all platforms (88 tests)
- Full platform validation
- Production-ready test suite

## Files to Investigate

### Device Creation
- `custom_components/abode_security/abode/client.py:435-495` - `_load_devices()` method
- `custom_components/abode_security/abode/devices/base.py:134-143` - `Device.new()` factory
- `custom_components/abode_security/abode/devices/binary_sensor.py` - BinarySensor class

### Platform Setup
- `custom_components/abode_security/binary_sensor.py` - Entity creation
- `custom_components/abode_security/entity.py` - Base entity class
- `custom_components/abode_security/models.py` - AbodeSystem wrapper

### Test Infrastructure
- `tests/conftest.py:68-108` - `mock_abode` fixture
- `tests/conftest.py:146-277` - `mock_server` fixture
- `tests/common.py:22-41` - `setup_platform` helper

## Related Documentation

- Phase 4: Test Infrastructure - Complete
- Phase 4.5.1: Import Refactoring - ✅ Complete (2025-12-18)
- Phase 4.5.2: Init Tests - ✅ Complete (referenced in phase-4-5.md)
- Phase 4.5: Overall strategy - See `phase-4-5.md`

## Time Estimates

- **Approach 2 Investigation**: 2-3 hours
- **First platform enabled**: 1-2 hours
- **All simple platforms**: 3-4 hours
- **All platforms**: 8-12 hours

## Notes

- Don't rush - proper device mocking is critical for test reliability
- Each enabled platform validates production code
- Tests should fail when code breaks (not pass with broken mocks)
- Consider this investment in long-term maintainability
