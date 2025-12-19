# Plan: Convert Alarm Control Panel Tests to Integration Tests

**Date:** 2025-12-19
**Phase:** 4.5.3 - Platform Tests with Mock Server
**Status:** Ready for Implementation

---

## Executive Summary

Convert 6 alarm_control_panel tests from unit tests (with extensive mocking) to integration tests using the mock server. Unlike other platforms, the alarm panel is **uniquely positioned** for full integration testing because the mock server already implements:
- `PUT /api/v1/panel/mode/{area}/{mode}` endpoint with real state changes
- SocketIO events emitted on mode changes (`com.goabode.states`)
- No need for device method mocking (unlike light/lock tests)

This enables true end-to-end testing: service call → HTTP request → SocketIO event → state update → verification.

---

## Current State

**Existing Tests** (tests/test_alarm_control_panel.py):
1. `test_entity_registry` - Validates MAC address unique_id
2. `test_attributes` - Validates state and attributes
3. `test_set_alarm_away` - Mocks callbacks to test arm away
4. `test_set_alarm_home` - Mocks callbacks to test arm home
5. `test_set_alarm_standby` - Mocks callbacks to test disarm
6. `test_state_unknown` - Tests unknown state with mocked mode property

**Current Pattern (Unit Test with Mocks):**
```python
with patch("abode.event_controller.EventController.add_device_callback"):
    with patch("abode.devices.alarm.Alarm.set_away"):
        await setup_platform(hass, ALARM_DOMAIN)
        # Manually trigger mocked callback
        update_callback = mock_callback.call_args[0][1]
        await hass.async_add_executor_job(update_callback, "area_1")
```

**Problems:**
- Manual callback triggering doesn't test real SocketIO flow
- Mocked methods don't validate HTTP request/response
- Tests pass even if SocketIO integration is broken

---

## Implementation Plan

### Test Conversion Pattern

**New Pattern (Integration Test):**
```python
@pytest.mark.integration
@pytest.mark.enable_socket
async def test_alarm_arm_away(
    hass: HomeAssistant,
    mock_server_client: dict[str, str]
) -> None:
    import importlib
    from custom_components.abode_security.abode.helpers import urls

    # 1. Setup environment
    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
    importlib.reload(urls)  # CRITICAL: Reload to apply env var

    try:
        # 2. Create config entry with SocketIO enabled
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,  # Enable SocketIO for real-time updates
            },
        )
        config_entry.add_to_hass(hass)

        # 3. Setup integration (makes real HTTP calls)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # 4. Call service (triggers real HTTP PUT → mock server → SocketIO event)
        await hass.services.async_call(
            ALARM_DOMAIN,
            SERVICE_ALARM_ARM_AWAY,
            {ATTR_ENTITY_ID: ALARM_ENTITY_ID},
            blocking=True,
        )
        await hass.async_block_till_done()

        # 5. Verify state updated via SocketIO
        state = hass.states.get(ALARM_ENTITY_ID)
        assert state.state == AlarmControlPanelState.ARMED_AWAY

    finally:
        # 6. Cleanup environment
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]
```

**Key Changes:**
- ✅ Remove all mocking (except test 6)
- ✅ Real HTTP calls to mock server
- ✅ Real SocketIO events for state updates
- ✅ Environment variable setup and cleanup
- ✅ Platform-specific test names

---

## Test Conversion Details

### Test 1: test_alarm_entity_registry

**Purpose:** Validate entity registration with MAC address unique_id

**Changes:**
- Add `@pytest.mark.integration` and `@pytest.mark.enable_socket`
- Add `mock_server_client` parameter
- Setup environment and reload urls module
- Use real config entry (remove `setup_platform` helper)
- Verify `unique_id == "001122334455"` (MAC from login.json: "00:11:22:33:44:55" without colons)

---

### Test 2: test_alarm_attributes

**Purpose:** Validate state and attributes

**Changes:**
- Same pattern as test 1
- Verify initial state: `AlarmControlPanelState.DISARMED`
- Verify attributes:
  - `device_id == "area_1"`
  - `battery_backup == False` (panel.json: "battery": "0")
  - `cellular_backup == False` (panel.json: "is_cellular": "0")
  - `ATTR_FRIENDLY_NAME == "Abode Alarm"`
  - `ATTR_SUPPORTED_FEATURES == 3`

---

### Test 3: test_alarm_arm_away

**Purpose:** Test arming to away mode with SocketIO state update

**Changes:**
- Remove callback mocking
- Remove device method mocking (`Alarm.set_away`)
- Call service → wait for SocketIO event → verify state
- Mock server handles: HTTP PUT → update state → emit event → callback → HA state update

---

### Test 4: test_alarm_arm_home

**Purpose:** Test arming to home mode

**Changes:**
- Same pattern as test 3
- Verify state changes to `AlarmControlPanelState.ARMED_HOME`

---

### Test 5: test_alarm_disarm

**Purpose:** Test disarming to standby mode

**Changes:**
- Same pattern as test 3
- **Extra step:** First arm alarm, then disarm (tests full cycle)
- Verify state changes to `AlarmControlPanelState.DISARMED`

---

### Test 6: test_alarm_state_unknown

**Purpose:** Test unknown state when mode is None

**Approach:** Hybrid - integration test setup with mode property mocking

**Changes:**
```python
# Setup integration normally, then mock mode property
with patch(
    "custom_components.abode_security.abode.devices.alarm.Alarm.mode",
    new_callable=PropertyMock,
) as mock_mode:
    mock_mode.return_value = None

    # Force entity update
    await hass.helpers.entity_component.async_update_entity(ALARM_ENTITY_ID)
    await hass.async_block_till_done()

    state = hass.states.get(ALARM_ENTITY_ID)
    assert state.state == "unknown"
```

**Rationale:** Can't simulate None mode with mock server, but can test property logic with minimal mocking.

---

## Test Naming Convention

**Critical:** Use platform-specific names to avoid conflicts

```python
# ❌ BAD - Generic names
test_entity_registry
test_attributes

# ✅ GOOD - Platform-specific names
test_alarm_entity_registry
test_alarm_attributes
test_alarm_arm_away
test_alarm_arm_home
test_alarm_disarm
test_alarm_state_unknown
```

---

## State Update Timing Strategy

**Approach:** Use `await hass.async_block_till_done()` (proven pattern)

**Rationale:**
- SocketIO events processed synchronously by Home Assistant
- `async_block_till_done()` waits for all tasks including SocketIO callbacks
- Proven to work in light/lock/cover/sensor tests
- No race conditions observed

**If timing issues arise:**
```python
await hass.async_block_till_done()
await asyncio.sleep(0.05)  # 50ms buffer for SocketIO processing
```

---

## Files to Modify

### 1. tests/test_alarm_control_panel.py (Primary)

**Changes:**
- Add imports:
  ```python
  import os
  from unittest.mock import PropertyMock, patch
  import pytest
  from pytest_homeassistant_custom_component.common import MockConfigEntry
  from custom_components.abode_security import DOMAIN
  from custom_components.abode_security.const import CONF_POLLING
  from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
  ```
- Convert 6 tests to integration pattern
- Rename tests with `test_alarm_*` prefix
- Remove `setup_platform` helper usage

**Order of conversion:**
1. `test_alarm_entity_registry` - Simplest
2. `test_alarm_attributes` - No service calls
3. `test_alarm_arm_away` - First service call
4. `test_alarm_arm_home` - Similar pattern
5. `test_alarm_disarm` - Multi-step test
6. `test_alarm_state_unknown` - Hybrid mocking

---

### 2. tests/conftest.py

**Changes:** Add to `enabled_tests` set (around line 67)

```python
enabled_tests = {
    # ... existing tests ...

    # Alarm control panel (6/6) - Phase 4.5.3
    "test_alarm_entity_registry",
    "test_alarm_attributes",
    "test_alarm_arm_away",
    "test_alarm_arm_home",
    "test_alarm_disarm",
    "test_alarm_state_unknown",
}
```

---

### 3. tests/test_constants.py

**Verification only** - Constants are already correct:
```python
ALARM_DEVICE_ID = "area_1"  # ✅
ALARM_UID = "001122334455"  # ✅ MAC without colons
ALARM_ENTITY_ID = "alarm_control_panel.abode_alarm"  # ✅
```

---

## Expected Challenges and Solutions

### Challenge 1: SocketIO Event Timing

**Symptom:** State not updated after service call

**Solution:**
```python
await hass.async_block_till_done()
await asyncio.sleep(0.05)  # Add small delay if needed
```

**Diagnostic:**
- Check mock server logs: `Emitting Socket.IO event: com.goabode.states`
- Verify `CONF_POLLING: False`
- Verify `@pytest.mark.enable_socket` present

---

### Challenge 2: Environment Variable Not Applied

**Symptom:** Tests connect to real API instead of mock server

**Root cause:** `urls` module imports at module level

**Solution:**
```python
import importlib
os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]
importlib.reload(urls)  # CRITICAL - must reload after env var change
```

---

### Challenge 3: MAC Address Mismatch

**Symptom:** Entity not found or unique_id assertion fails

**Investigation:**
- login.json: `"mac": "00:11:22:33:44:55"`
- Alarm.uuid: `self.mac.replace(':', '').lower()` → `"001122334455"`
- ALARM_UID must match: `"001122334455"`

**Solution:** Constants already correct, no changes needed

---

### Challenge 4: Test State Unknown Mocking

**Issue:** Mocking `Alarm.mode` in integration test

**Solution:**
```python
# Force entity update after mocking
with patch("custom_components.abode_security.abode.devices.alarm.Alarm.mode", ...):
    await hass.helpers.entity_component.async_update_entity(ALARM_ENTITY_ID)
    await hass.async_block_till_done()
```

**Alternative:** Keep as pure unit test (acceptable if hybrid doesn't work)

---

## Testing Strategy

### Per-Test Development

```bash
# Test single conversion
pytest tests/test_alarm_control_panel.py::test_alarm_entity_registry -v

# With coverage
pytest tests/test_alarm_control_panel.py::test_alarm_entity_registry \
  -v --cov=custom_components.abode_security.alarm_control_panel
```

### Full Suite Testing

```bash
# All alarm tests
pytest tests/test_alarm_control_panel.py -v

# Expected: 6 passed in ~2-3 seconds
```

### Pre-Commit Validation

```bash
# Run pre-commit hook (ruff, mypy, pytest)
.githooks/pre-commit

# All checks must pass before commit
```

---

## Commit Strategy

### Commit 1: Basic tests (entity registry + attributes)

```
feat: Convert alarm entity registry and attributes tests (Phase 4.5.3)

- Convert test_entity_registry to test_alarm_entity_registry
- Convert test_attributes to test_alarm_attributes
- Use mock server with SocketIO enabled
- Remove mocking, use real HTTP calls
- Add tests to enabled_tests in conftest.py

Part of Phase 4.5.3 - alarm control panel integration tests
```

**Files:** test_alarm_control_panel.py, conftest.py

---

### Commit 2: Service call tests (arm/disarm)

```
feat: Convert alarm service call tests to integration tests (Phase 4.5.3)

- Convert test_set_alarm_away to test_alarm_arm_away
- Convert test_set_alarm_home to test_alarm_arm_home
- Convert test_set_alarm_standby to test_alarm_disarm
- Tests use real SocketIO events for state updates
- Remove manual callback triggering and mocking
- Add tests to enabled_tests in conftest.py

Part of Phase 4.5.3 - alarm control panel integration tests
```

**Files:** test_alarm_control_panel.py, conftest.py

---

### Commit 3: Unknown state test (hybrid)

```
feat: Convert alarm unknown state test to integration test (Phase 4.5.3)

- Convert test_state_unknown to test_alarm_state_unknown
- Use hybrid approach: integration setup + mode mocking
- Tests edge case where mode is None
- Add test to enabled_tests in conftest.py

Completes Phase 4.5.3 - all 6 alarm control panel tests enabled
```

**Files:** test_alarm_control_panel.py, conftest.py

---

## Success Criteria

**Test Execution:**
- ✅ All 6 tests pass
- ✅ No skipped tests
- ✅ Complete in < 5 seconds
- ✅ No flaky failures (3 runs, all pass)

**Coverage:**
- ✅ alarm_control_panel.py ≥ 85% coverage
- ✅ All entity states tested (DISARMED, ARMED_AWAY, ARMED_HOME, unknown)
- ✅ All service calls tested

**Code Quality:**
- ✅ Minimal mocking (only test 6)
- ✅ SocketIO events used for state updates
- ✅ Environment properly restored
- ✅ Platform-specific test names
- ✅ Pre-commit hooks pass

**Integration:**
- ✅ Works with Docker mock server
- ✅ Tests properly isolated
- ✅ No interference with other platforms

---

## Expected Coverage

**Current:** ~69%
**Target:** 85-90%

**Covered by tests:**
- ✅ `alarm_state` property (all 4 states)
- ✅ `async_alarm_disarm`
- ✅ `async_alarm_arm_home`
- ✅ `async_alarm_arm_away`
- ✅ `extra_state_attributes`

**Not covered (acceptable):**
- ❌ `trigger_manual_alarm` - No test exists
- ❌ `acknowledge_timeline_event` - No test exists
- ❌ `dismiss_timeline_event` - No test exists

**Note:** Uncovered methods are advanced features not tested in current suite. Document for future expansion.

---

## Mock Server Capabilities (Already Implemented)

**Endpoints:**
- ✅ `GET /api/v1/panel` - Returns panel with mode
- ✅ `PUT /api/v1/panel/mode/{area}/{mode}` - Sets mode, emits SocketIO
- ✅ `POST /integrations/v1/panel/alarm` - Triggers manual alarm

**SocketIO:**
- ✅ Server running at `/socket.io/`
- ✅ Emits `com.goabode.states` events on mode changes
- ✅ Event payload: `{id, type_tag, mode, area}`

**State Management:**
- ✅ In-memory `panel_mode` state
- ✅ `reset_mock_server` fixture resets between tests
- ✅ Fixture data from panel.json

**No mock server changes needed - fully functional!**

---

## Reference Files

**Implementation patterns:**
- tests/test_lock.py - Similar service call pattern
- tests/test_light.py - SocketIO event handling
- tests/test_cover.py - State update verification

**Mock server:**
- tests/mock_server/main.py (lines 174-215) - Panel mode endpoint
- tests/fixtures/panel.json - Panel fixture data
- tests/fixtures/login.json - MAC address for unique_id

**Integration code:**
- custom_components/abode_security/alarm_control_panel.py - Entity implementation
- custom_components/abode_security/abode/devices/alarm.py - Device implementation
- custom_components/abode_security/entity.py (lines 69-80) - Callback registration

---

## Next Steps

1. Start with test 1 (entity_registry) - validate pattern works
2. Convert test 2 (attributes) - validate attributes logic
3. Convert tests 3-5 (service calls) - validate SocketIO flow
4. Convert test 6 (unknown state) - validate hybrid mocking
5. Run full test suite
6. Verify coverage ≥ 85%
7. Commit in 3 logical chunks
8. Update phase-4-5-3-platform-tests.md documentation

**Estimated time:** 1-2 hours for all 6 tests + commits + documentation
