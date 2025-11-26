# Phase 5 Development Plan - Native Async Conversion

**Date:** 2024-11-24
**Status:** Phase 5 📋 Planned (Ready to Start)
**Foundation:** Phase 4A & 4B Complete with Vendored Library
**Target:** Native async/await support for the vendored Abode library
**Estimated Effort:** 28-44 hours over 2-3 weeks

---

## Executive Summary

Phase 5 focuses on converting the vendored `abode` library (located in `/lib/abode`) from synchronous to native async/await support. This is a major technical undertaking that will eliminate the need for executor-based wrappers and provide true non-blocking asynchronous operations.

### Phase 5 Opportunity

The codebase now has a **critical advantage**: the `jaraco.abode` library has been **vendored locally** in `/lib/abode`, which means we have full control over the library code and can implement native async support without waiting for upstream changes or maintaining a fork.

### Key Objectives

1. ✅ Convert the vendored Abode library to native async/await
2. ✅ Eliminate executor job wrappers in the integration
3. ✅ Maintain 100% backward compatibility with existing code
4. ✅ Ensure all tests pass with async operations
5. ✅ Maintain ruff linting compliance (100% pass)
6. ✅ Update documentation for async architecture

---

## Current State Analysis

### Existing Foundation

**Vendored Library Location:** `/lib/abode/`
- ✅ Full control of library code
- ✅ Can modify without external dependencies
- ✅ Currently synchronous with blocking I/O

**Current Integration Usage:** `custom_components/abode_security/__init__.py`
```python
# Currently uses executor wrapper:
abode_client = await hass.async_add_executor_job(
    Abode, username, password, True, True, True
)
```

**Async Wrapper:** `custom_components/abode_security/async_wrapper.py`
- 10+ async methods that use executor jobs internally
- Can be simplified once library is truly async

### Files to Convert (Priority Order)

**Critical Path (Must Do First):**
1. `/lib/abode/client.py` - Core Client class with main API methods
2. `/lib/abode/event_controller.py` - Event handling and subscriptions
3. `/lib/abode/socketio.py` - WebSocket connections (perfect for async!)

**High Priority (Required Before Integration):**
4. `/lib/abode/devices/base.py` - Base device class
5. `/lib/abode/devices/alarm.py` - Alarm-specific operations
6. `/lib/abode/automation.py` - Automation control methods

**Medium Priority (Supporting Infrastructure):**
7. `/lib/abode/helpers/` - Helper modules (may have I/O operations)
8. Other device type files in `/lib/abode/devices/`

---

## Phase 5 Implementation Plan

### 1. HTTP Client Conversion (8-12 hours)

**Objective:** Replace `requests` library with `aiohttp` for async HTTP operations

#### 1.1 Dependency Analysis
- [x] Identify all `requests` usage in `/lib/abode/client.py`
- [x] Check for session management patterns
- [x] Identify cookies and auth handling
- [ ] Plan migration from requests.Session to aiohttp.ClientSession

#### 1.2 Core Client (`/lib/abode/client.py`)
- [ ] Replace `import requests` with `import aiohttp`
- [ ] Convert `__init__` to accept async context manager patterns
- [ ] Convert `_cookies()` function to async
- [ ] Convert HTTP methods: `login()`, `get()`, `post()`, `set_setting()`
- [ ] Update session management for async lifecycle
- [ ] Add proper cleanup (session closing)

**Key Methods to Convert:**
```python
# Before (synchronous)
def login(self, username, password, mfa_code=None):
    response = self._session.post(urls.LOGIN, json=login_data)
    return response.json()

# After (async)
async def login(self, username, password, mfa_code=None):
    async with self._session.post(urls.LOGIN, json=login_data) as response:
        return await response.json()
```

#### 1.3 Testing
- [ ] Create unit tests for async HTTP methods
- [ ] Test session lifecycle (creation, cleanup)
- [ ] Test error handling with aiohttp exceptions
- [ ] Test timeouts and retries

**Estimated Effort:** 8-12 hours

---

### 2. Event Controller Conversion (8-12 hours)

**Objective:** Convert WebSocket event handling to async

#### 2.1 Event Controller (`/lib/abode/event_controller.py`)
- [ ] Analyze current event subscription pattern
- [ ] Convert `add_event_callback()` to `async def`
- [ ] Convert `remove_event_callback()` to `async def`
- [ ] Convert `start()` to async lifecycle
- [ ] Convert `stop()` to async cleanup

#### 2.2 SocketIO Integration (`/lib/abode/socketio.py`)
- [ ] Evaluate current socketio implementation
- [ ] Consider `python-socketio` (async-compatible)
- [ ] Convert WebSocket listener to async
- [ ] Update event emission to async callbacks
- [ ] Implement proper async context management

**Key Pattern:**
```python
# Event callbacks with async support
async def on_event(self, event_group, callback):
    """Register async callback for events"""
    async def wrapper(event_data):
        if asyncio.iscoroutinefunction(callback):
            await callback(event_data)
        else:
            callback(event_data)
    self._add_listener(event_group, wrapper)
```

#### 2.3 Testing
- [ ] Test event subscription/unsubscription
- [ ] Test async callback execution
- [ ] Test mixed sync/async callbacks (backward compatibility)
- [ ] Test connection lifecycle

**Estimated Effort:** 8-12 hours

---

### 3. Device Operations Conversion (6-10 hours)

**Objective:** Convert all device control methods to async

#### 3.1 Base Device Class (`/lib/abode/devices/base.py`)
- [ ] Convert device fetch/refresh methods to async
- [ ] Update property access patterns if needed
- [ ] Convert any HTTP-based device operations to async

#### 3.2 Alarm Device (`/lib/abode/devices/alarm.py`)
- [ ] Convert `set_standby()` to async
- [ ] Convert `set_home()` to async
- [ ] Convert `set_away()` to async
- [ ] Convert `set_test_mode()` to async
- [ ] Update any timeline event methods to async

#### 3.3 Other Devices (Switches, Locks, Covers, Sensors, etc.)
- [ ] Convert all device control methods to async
- [ ] Update device state refresh methods
- [ ] Convert battery/status queries to async

**Example Conversion:**
```python
# Before
def switch_on(self):
    return self._client.set_status(self.device_id, 1)

# After
async def switch_on(self):
    return await self._client.set_status(self.device_id, 1)
```

#### 3.4 Automation Control (`/lib/abode/automation.py`)
- [ ] Convert `trigger()` to async
- [ ] Convert automation state methods to async

**Estimated Effort:** 6-10 hours

---

### 4. Integration Refactoring (6-10 hours)

**Objective:** Update the Home Assistant integration to use native async

#### 4.1 Main Integration (`custom_components/abode_security/__init__.py`)
- [ ] Remove executor wrapper for Client instantiation
- [ ] Update `async_setup_entry()` to use async Client initialization
- [ ] Handle async context manager if needed
- [ ] Update event subscription patterns

**Current Code:**
```python
abode_client = await hass.async_add_executor_job(
    Abode, username, password, True, True, True
)
```

**After Conversion:**
```python
abode_client = Abode(username, password, True, True, True)
await abode_client.async_initialize()  # If needed
```

#### 4.2 Async Wrapper Simplification (`custom_components/abode_security/async_wrapper.py`)
- [ ] Remove executor wrappers from all methods
- [ ] Convert to direct async calls on Client
- [ ] Simplify or remove helper functions that are no longer needed
- [ ] Keep batch operations for performance optimization

**Before:**
```python
async def async_get_alarm(hass, abode_client):
    return await async_call(hass, abode_client.get_alarm)
```

**After:**
```python
async def async_get_alarm(hass, abode_client):
    return await abode_client.get_alarm()  # Now truly async!
```

#### 4.3 Entity Updates
- [ ] Update all platform entities to use async methods
- [ ] Verify entity setup completes correctly
- [ ] Test entity state updates with async operations
- [ ] Ensure polling works with async Client

**Estimated Effort:** 6-10 hours

---

### 5. Testing & Validation (6-10 hours)

**Objective:** Ensure all tests pass and functionality is preserved

#### 5.1 Unit Tests
- [ ] Update existing tests to work with async Client
- [ ] Add tests for new async methods
- [ ] Test error handling in async context
- [ ] Test timeout and retry behavior

#### 5.2 Integration Tests
- [ ] Run all integration tests
- [ ] Verify entity setup completes
- [ ] Test config flow works correctly
- [ ] Test options flow with async operations

#### 5.3 End-to-End Tests
- [ ] Test full setup workflow with async
- [ ] Test device discovery and creation
- [ ] Test service calls with async operations
- [ ] Test error recovery scenarios

#### 5.4 Code Quality
- [ ] Run ruff linting (must pass 100%)
- [ ] Check for unused imports from removed executor code
- [ ] Verify type hints are correct for async methods
- [ ] Test on actual Home Assistant instance (if available)

#### 5.5 Backward Compatibility
- [ ] Ensure async wrappers still work with sync code
- [ ] Test mixed async/sync callbacks
- [ ] Verify no breaking changes to public API

**Estimated Effort:** 6-10 hours

---

## Technical Considerations

### Async Context Management

The Abode Client will need proper lifecycle management:

```python
class Client:
    async def __aenter__(self):
        """Async context manager entry"""
        await self._async_initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.logout()
```

### Backward Compatibility Pattern

To maintain backward compatibility with sync code where needed:

```python
def _run_async(coro):
    """Helper to run async code from sync context (if absolutely needed)"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)
```

### Session Lifecycle

Proper cleanup is critical:

```python
# In __init__.py
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload and cleanup async resources"""
    abode_system = entry.runtime_data
    await abode_system.abode_client.cleanup()  # Close session, etc.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

---

## Potential Challenges & Solutions

### Challenge 1: Circular Imports
**Risk:** Converting to async may introduce circular import issues
**Solution:** Use TYPE_CHECKING guards and lazy imports

### Challenge 2: Third-Party Dependencies
**Risk:** Some vendored dependencies may not support async
**Solution:** Wrap or replace incompatible dependencies

### Challenge 3: Callback Handling
**Risk:** Code that registers callbacks may expect sync functions
**Solution:** Support both async and sync callbacks with wrapper

### Challenge 4: Context Variables
**Risk:** Loss of request context in async context
**Solution:** Use contextvars if needed, but Home Assistant handles this

### Challenge 5: Tests with Mocks
**Risk:** Existing mocks may not work with async code
**Solution:** Update conftest.py fixtures to support async mocking

---

## Success Criteria

### Phase 5 Complete When:

- ✅ All HTTP operations use aiohttp (no more requests library)
- ✅ All event operations are async (no executor wrappers)
- ✅ All device operations support async (lock/unlock, switch on/off, etc.)
- ✅ Integration no longer uses executor jobs for library calls
- ✅ All 126+ tests pass with async code
- ✅ Ruff linting passes 100% on all changes
- ✅ Zero performance regression (same or faster response times)
- ✅ Backward compatibility maintained where reasonable
- ✅ Documentation updated for async architecture

---

## Commit Strategy

Plan commits in logical chunks:

1. **HTTP Client Conversion**
   - Replace requests with aiohttp
   - Update login and HTTP methods
   - Tests for HTTP layer

2. **Event Controller Conversion**
   - Async event subscriptions
   - WebSocket async handling
   - Event callback tests

3. **Device Operations Conversion**
   - Convert all device methods to async
   - Update alarm operations
   - Device operation tests

4. **Integration Refactoring**
   - Remove executor wrappers
   - Update entity code
   - Integration tests

5. **Code Cleanup**
   - Fix ruff issues
   - Import cleanup
   - Remove unused async_wrapper helpers

6. **Final Testing & Documentation**
   - All tests passing
   - Update documentation
   - Performance verification

---

## Next Claude Session Prompt

When starting Phase 5, use this prompt:

```
You're continuing the Abode Security Home Assistant integration project.
Phase 4A & 4B are complete (advanced features, testing, production-ready).

Now it's time for Phase 5: Native Async Conversion

The project has vendored the jaraco.abode library locally in /lib/abode,
which gives us full control to convert it to native async/await support.

CRITICAL CONTEXT:
- Vendored library path: /lib/abode/
- Current state: Synchronous with executor job wrappers
- Goal: Native async/await throughout
- Integration location: custom_components/abode_security/

PHASE 5 TASKS (28-44 hours estimated):
1. HTTP Client Conversion (8-12 hours)
   - Replace requests with aiohttp
   - Convert all HTTP methods in /lib/abode/client.py
   - Handle session lifecycle properly

2. Event Controller Conversion (8-12 hours)
   - Make /lib/abode/event_controller.py async
   - Convert WebSocket handling in /lib/abode/socketio.py
   - Support async event callbacks

3. Device Operations Conversion (6-10 hours)
   - Convert all device methods to async
   - Update alarm, switches, locks, covers, etc.
   - Convert automation control to async

4. Integration Refactoring (6-10 hours)
   - Remove executor wrappers from integration
   - Update async_wrapper.py to use native async
   - Update entity implementations

5. Testing & Validation (6-10 hours)
   - Update all 126+ tests
   - Ensure ruff 100% compliance
   - Verify backward compatibility
   - Performance testing

REQUIREMENTS:
- Use aiohttp for HTTP operations (async-native)
- Maintain ruff 100% linting compliance
- Keep all 126+ tests passing
- Support both async and sync callbacks (backward compat)
- Zero breaking changes to public API
- Document all async patterns

SUCCESS METRICS:
✅ No more executor job wrappers in integration
✅ All HTTP uses aiohttp (no requests library)
✅ All tests pass with async code
✅ Ruff linting 100% pass
✅ Same or better performance
✅ Full async/await throughout library

Start by reading .claude/PHASE_5_PLAN.md for detailed implementation guide.
Read /lib/abode/client.py to understand current HTTP pattern.
Then begin with HTTP client conversion (highest priority).

Make commits as you complete each section. After each commit, run ruff linting.
```

---

## Implementation Roadmap

### Session 1 (6-8 hours): HTTP Client Conversion
- Analyze requests usage
- Implement aiohttp ClientSession
- Convert core HTTP methods
- Write tests

### Session 2 (6-8 hours): Event Controller Conversion
- Convert event subscriptions to async
- Update WebSocket handling
- Implement async callback support
- Write integration tests

### Session 3 (6-8 hours): Device Operations Conversion
- Convert device methods to async
- Update all platform devices
- Update automation control
- Write device tests

### Session 4 (6-8 hours): Integration & Testing
- Remove executor wrappers
- Update async_wrapper.py
- Run full test suite
- Fix ruff issues
- Final documentation

---

## Key Files Reference

### Vendored Library Structure
```
/lib/abode/
├── __init__.py              # Package init
├── client.py                # ← MAIN: HTTP client (CONVERT FIRST)
├── event_controller.py       # ← Event handling (HIGH PRIORITY)
├── socketio.py              # ← WebSocket (CONVERT WITH EVENT CONTROLLER)
├── automation.py            # Automation control
├── devices/
│   ├── base.py             # Base device class
│   ├── alarm.py            # ← Alarm-specific (HIGH PRIORITY)
│   ├── switch.py
│   ├── lock.py
│   ├── cover.py
│   ├── sensor.py
│   ├── light.py
│   └── camera.py
├── helpers/
│   ├── urls.py
│   ├── errors.py
│   └── timeline.py
├── config.py               # Configuration
├── state.py                # State management
└── exceptions.py           # Custom exceptions
```

### Integration Files to Update
```
custom_components/abode_security/
├── __init__.py             # ← Main integration (REMOVE EXECUTOR WRAPPERS)
├── async_wrapper.py        # ← Simplify/remove (USE NATIVE ASYNC)
├── models.py               # Update if needed
├── config_flow.py          # Usually fine
├── services.py             # Update service handlers
├── entity.py               # Base entity
├── platforms/
│   ├── alarm_control_panel.py
│   ├── binary_sensor.py
│   ├── camera.py
│   ├── cover.py
│   ├── light.py
│   ├── lock.py
│   ├── sensor.py
│   └── switch.py
└── tests/
    ├── conftest.py         # Update fixtures
    ├── test_*.py           # Update all tests
    └── common.py           # Update helpers
```

---

## Dependencies to Add (If Needed)

- `aiohttp` - Already likely available in Home Assistant
- `python-socketio` - For async WebSocket support (check if already vendored)
- Type annotations: `AsyncContextManager`, `AsyncIterator` from `typing` or `collections.abc`

---

## Documentation Updates Needed

After Phase 5 completion:

1. **ARCHITECTURE.md** - Update async architecture
2. **DEVELOPMENT.md** - Update async development guide
3. **Code comments** - Document async patterns used
4. **Type hints** - Full async method signatures

---

## Estimated Timeline

- **Total Effort:** 28-44 hours
- **Recommended Pace:** 6-8 hours per session over 4-5 sessions
- **Timeline:** 2-3 weeks depending on session frequency

---

## Important Notes

### Do NOT:
- Break existing functionality
- Remove features working in Phase 4
- Create new executor wrappers
- Skip tests (must maintain 100% passing)

### DO:
- Run ruff after each commit
- Test on actual Home Assistant if possible
- Document async patterns clearly
- Keep commits logical and reviewable
- Verify backward compatibility

### Remember:
- Vendored library gives full control
- No need to wait for upstream changes
- This is a technical improvement, not a feature change
- Focus on correctness over speed
- Tests will catch breaking changes

---

## Review Checklist Before Completing Phase 5

- [ ] All HTTP operations use aiohttp
- [ ] All event operations are async
- [ ] All device methods are async
- [ ] No executor jobs in integration code
- [ ] All 126+ tests passing
- [ ] Ruff linting 100% pass
- [ ] No performance regression
- [ ] Documentation updated
- [ ] Backward compatibility verified
- [ ] Code review complete

---

**Document Created:** 2025-11-24
**Version:** 1.0
**Status:** Ready for Phase 5 Implementation
**Preconditions Met:** Yes ✅
  - Phase 4A & 4B Complete
  - Vendored library in place
  - All tests passing (126 methods)
  - 100% ruff compliance
  - Documentation current

**Next Action:** Begin Phase 5 when ready with provided prompt above
