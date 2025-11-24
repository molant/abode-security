# Phase 1.5: Code Quality & Deduplication Guide

## Overview

Phase 1.5 focuses on reducing code duplication and improving test coverage. This phase comes after Phase 2 (Quality Improvements) is complete and prepares the codebase for easier maintenance and future feature development.

**Current State:** The integration is working well with good test coverage, but there's significant boilerplate that can be consolidated.

## Phase 1.5 Tasks (In Order)

### 1. Create Error Handling Decorator

**Goal:** Consolidate repeated exception handling patterns across the codebase

**Current Problem:**
Exception handling with logging appears in 7+ locations:
- [switch.py:288-304](../custom_components/abode_security/switch.py#L288-L304) - `turn_on()`
- [switch.py:308-317](../custom_components/abode_security/switch.py#L308-L317) - `turn_off()`
- [switch.py:378-385](../custom_components/abode_security/switch.py#L378-L385) - Event callback
- [alarm_control_panel.py:70-92](../custom_components/abode_security/alarm_control_panel.py#L70-L92) - Multiple methods
- [models.py:25-47](../custom_components/abode_security/models.py#L25-L47) - Wrapper methods
- All service handlers in [services.py](../custom_components/abode_security/services.py)

**Pattern to eliminate:**
```python
try:
    # ... API call ...
except AbodeException as ex:
    LOGGER.error("Failed to...: %s", ex)
```

**Solution:**
Create `custom_components/abode_security/decorators.py`:

```python
"""Decorators for common operations."""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from .const import LOGGER
from .exceptions import AbodeException

_T = TypeVar("_T")


def handle_abode_errors(operation_name: str) -> Callable:
    """Decorator to handle Abode API exceptions consistently.

    Args:
        operation_name: Human-readable operation description for logging

    Returns:
        Decorated function that catches AbodeException and logs errors
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except AbodeException as ex:
                LOGGER.error(f"Failed to {operation_name}: %s", ex)
                return None

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except AbodeException as ex:
                LOGGER.error(f"Failed to {operation_name}: %s", ex)
                return None

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
```

**Files to update:**
1. [switch.py](../custom_components/abode_security/switch.py) - AbodeManualAlarmSwitch methods
2. [alarm_control_panel.py](../custom_components/abode_security/alarm_control_panel.py) - All control methods
3. [models.py](../custom_components/abode_security/models.py) - Wrapper methods

**Expected outcome:**
- Reduce boilerplate by ~50 lines
- Centralize error handling logic
- Easier to update error behavior globally

---

### 2. Create Service Handler Factory

**Goal:** Consolidate 5 nearly identical service handlers into a factory pattern

**Current Problem:**
All service handlers in [services.py](../custom_components/abode_security/services.py) follow identical structure:
- `_trigger_alarm()`
- `_acknowledge_alarm()`
- `_dismiss_alarm()`
- `_enable_test_mode()`
- `_disable_test_mode()`

Each repeats:
```python
async def _service_handler(call: ServiceCall) -> None:
    abode_system = _get_abode_system(call.hass)
    if not abode_system:
        LOGGER.error("Abode integration not configured")
        return
    try:
        await call.hass.async_add_executor_job(method, ...)
    except AbodeException as ex:
        LOGGER.error("Failed: %s", ex)
```

**Solution:**
Create factory function in [services.py](../custom_components/abode_security/services.py):

```python
def _create_service_handler(
    method_name: str,
    operation_desc: str,
    *arg_extractors: tuple[str, Callable[[ServiceCall], Any]],
) -> Callable:
    """Factory for creating service handlers with consistent error handling.

    Args:
        method_name: Name of method on abode_system.abode
        operation_desc: Human-readable description for logging
        arg_extractors: Tuples of (arg_name, extractor_func) for service data

    Returns:
        Service handler function ready to register
    """
    async def handler(call: ServiceCall) -> None:
        abode_system = _get_abode_system(call.hass)
        if not abode_system:
            LOGGER.error("Abode integration not configured")
            return

        try:
            method = getattr(abode_system.abode, method_name)
            args = [extractor(call) for _, extractor in arg_extractors]
            await call.hass.async_add_executor_job(method, *args)
            LOGGER.debug(f"Successfully {operation_desc}")
        except AbodeException as ex:
            LOGGER.error(f"Failed to {operation_desc}: %s", ex)

    return handler
```

**Usage example:**
```python
# Register trigger alarm service
hass.services.async_register(
    DOMAIN,
    SERVICE_TRIGGER_ALARM,
    _create_service_handler("trigger", "trigger alarm"),
)

# Register acknowledge alarm service with device_id parameter
hass.services.async_register(
    DOMAIN,
    SERVICE_ACKNOWLEDGE_ALARM,
    _create_service_handler(
        "acknowledge",
        "acknowledge alarm",
        ("device_id", lambda call: call.data.get(ATTR_DEVICE_ID)),
    ),
)
```

**Expected outcome:**
- Reduce [services.py](../custom_components/abode_security/services.py) by ~80 lines
- Single source of truth for service handler behavior
- Easier to add new services in the future

---

### 3. Create Event Callback Helpers

**Goal:** Consolidate event subscription/unsubscription logic

**Current Problem:**
[switch.py:196-230](../custom_components/abode_security/switch.py#L196-L230) has nearly identical subscribe and unsubscribe patterns.

**Solution:**
Add helper methods to `AbodeManualAlarmSwitch` class:

```python
async def _subscribe_to_events(
    self,
    event_group: TimelineGroups,
    callback: Callable,
) -> None:
    """Subscribe to Abode timeline events."""
    try:
        await self.hass.async_add_executor_job(
            self._data.abode.events.add_event_callback,
            event_group,
            callback,
        )
        LOGGER.debug(f"Subscribed to {event_group} events")
    except Exception as ex:
        LOGGER.warning(f"Could not subscribe to {event_group} events: %s", ex)

async def _unsubscribe_from_events(
    self,
    event_group: TimelineGroups,
    callback: Callable,
) -> None:
    """Unsubscribe from Abode timeline events."""
    if not hasattr(self._data.abode.events, "remove_event_callback"):
        LOGGER.debug("remove_event_callback not available, skipping unsubscribe")
        return

    try:
        await self.hass.async_add_executor_job(
            self._data.abode.events.remove_event_callback,
            event_group,
            callback,
        )
        LOGGER.debug(f"Unsubscribed from {event_group} events")
    except Exception as ex:
        LOGGER.warning(f"Could not unsubscribe from {event_group} events: %s", ex)
```

**Update `async_added_to_hass()`:**
```python
async def async_added_to_hass(self) -> None:
    """When entity is added to Home Assistant."""
    await super().async_added_to_hass()
    await self._subscribe_to_events(TimelineGroups.ALARM, self._alarm_event_callback)
    await self._subscribe_to_events(TimelineGroups.ALARM, self._alarm_end_callback)
```

**Update `async_will_remove_from_hass()`:**
```python
async def async_will_remove_from_hass(self) -> None:
    """When entity is removed from Home Assistant."""
    await self._unsubscribe_from_events(TimelineGroups.ALARM, self._alarm_event_callback)
    await self._unsubscribe_from_events(TimelineGroups.ALARM, self._alarm_end_callback)
    await super().async_will_remove_from_hass()
```

**Expected outcome:**
- Cleaner code with better error handling
- Easier to test event callback lifecycle
- Reduces nested try-except blocks

---

### 4. Centralize Test Constants

**Goal:** Move scattered test constants to single location

**Current Problem:**
Test files define similar constants in each file:
- `test_switch.py` - DEVICE_ID, AUTOMATION_ID, etc.
- `test_alarm_control_panel.py` - Different DEVICE_ID
- `test_binary_sensor.py` - Entity ID strings
- Other test files - Similar duplications

**Solution:**
Create `tests/test_constants.py`:

```python
"""Shared constants for all tests."""

from __future__ import annotations

# Device IDs from fixtures
DEVICE_ID = "51bd4e50"  # Switch device
ALARM_DEVICE_ID = "e5c4f0d0"  # Alarm/control panel
AUTOMATION_ID = "1"  # First automation
LIGHT_DEVICE_ID = "123abc"  # Light device
LOCK_DEVICE_ID = "456def"  # Lock device

# Unique IDs
DEVICE_UID = "51bd4e50-switch"
ALARM_UID = "e5c4f0d0-alarm"
AUTOMATION_UID = "1-automation"
LIGHT_UID = "123abc-light"
LOCK_UID = "456def-lock"

# Entity IDs
SWITCH_ENTITY_ID = "switch.living_room_fan"
AUTOMATION_ENTITY_ID = "switch.automation_control"
ALARM_ENTITY_ID = "alarm_control_panel.alarm"
LIGHT_ENTITY_ID = "light.living_room_light"
LOCK_ENTITY_ID = "lock.front_door"

# Common test data
DOMAIN = "abode_security"
```

**Update all test files:**
```python
from tests.test_constants import DEVICE_ID, SWITCH_ENTITY_ID, DEVICE_UID
```

**Expected outcome:**
- Single source of truth for test fixtures
- Easier to maintain and update tests
- Reduced duplication across test files

---

### 5. Add Entity Lifecycle Tests

**Goal:** Test initialization and cleanup of entities

**Create file:** `tests/test_entity_lifecycle.py`

**Tests to add:**

1. **Entity initialization tests:**
```python
async def test_manual_alarm_switch_subscribes_to_events(hass, mock_abode):
    """Test that alarm switch subscribes to timeline events on init."""
    mock_abode.events.add_event_callback = AsyncMock()

    await setup_platform(hass, DOMAIN)

    # Verify callback was registered
    mock_abode.events.add_event_callback.assert_called()
    calls = mock_abode.events.add_event_callback.call_args_list
    assert any(TimelineGroups.ALARM in str(call) for call in calls)
```

2. **Entity cleanup tests:**
```python
async def test_manual_alarm_switch_unsubscribes_on_removal(hass, mock_abode):
    """Test that alarm switch unsubscribes from events on removal."""
    mock_abode.events.remove_event_callback = AsyncMock()

    await setup_platform(hass, DOMAIN)

    # Get the entity and remove it
    state = hass.states.get(ALARM_ENTITY_ID)
    assert state is not None

    # Simulate entity removal
    # Verify callback was unregistered
    mock_abode.events.remove_event_callback.assert_called()
```

3. **Error recovery tests:**
```python
async def test_manual_alarm_switch_handles_missing_remove_callback(hass, mock_abode):
    """Test graceful handling when remove_event_callback doesn't exist."""
    delattr(mock_abode.events, "remove_event_callback")

    await setup_platform(hass, DOMAIN)

    # Should not raise, even though method is missing
    # (Tested via removal or by calling the method directly)
```

4. **Fallback tests for models.py:**
```python
async def test_get_test_mode_returns_false_when_method_missing(hass):
    """Test that get_test_mode returns False if method doesn't exist."""
    abode_system = AbodeSystem(
        abode=Mock(spec=[]),  # No methods
        polling=False,
        entity_ids=set(),
        logout_listener=None,
    )

    result = abode_system.get_test_mode()
    assert result is False

async def test_set_test_mode_handles_exception_gracefully(hass):
    """Test that set_test_mode logs but doesn't raise on error."""
    mock_abode = Mock()
    mock_abode.set_test_mode.side_effect = Exception("API error")

    abode_system = AbodeSystem(
        abode=mock_abode,
        polling=False,
        entity_ids=set(),
        logout_listener=None,
    )

    # Should not raise
    abode_system.set_test_mode(True)
```

**Expected outcome:**
- Better test coverage of edge cases
- Catches regressions in lifecycle management
- Ensures error handling works as expected

---

### 6. Add Event Callback Event Code Extraction

**Goal:** Extract event code mapping logic from callbacks

**Current Problem:**
[switch.py:234-280](../custom_components/abode_security/switch.py#L234-L280) has event code mapping duplicated in two callback methods.

**Solution:**
Create helper function in [switch.py](../custom_components/abode_security/switch.py):

```python
def _map_event_code_to_alarm_type(event_code: str) -> str | None:
    """Map Abode event code to alarm type.

    Args:
        event_code: Numeric event code from Abode API

    Returns:
        Alarm type (burglar, fire, panic) or None if unknown
    """
    event_code_mapping = {
        "2100": "burglar",
        "2101": "fire",
        "2102": "panic",
    }
    return event_code_mapping.get(event_code)
```

**Update callbacks:**
```python
def _alarm_event_callback(self, event: dict[str, Any]) -> None:
    """Handle alarm event from Abode timeline."""
    event_code = event.get("code", "")
    alarm_type = _map_event_code_to_alarm_type(event_code)

    if not alarm_type:
        LOGGER.debug(f"Unknown alarm event code: {event_code}")
        return

    # Use alarm_type...

def _alarm_end_callback(self, event: dict[str, Any]) -> None:
    """Handle alarm end event from Abode timeline."""
    event_code = event.get("code", "")
    alarm_type = _map_event_code_to_alarm_type(event_code)

    if not alarm_type:
        LOGGER.debug(f"Unknown alarm end code: {event_code}")
        return

    # Use alarm_type...
```

**Expected outcome:**
- Centralized event code mapping
- Easier to add new event types
- Cleaner callback methods

---

## Testing Phase 1.5 Changes

After each task:

```bash
# Run tests
pytest tests/ -v

# Check formatting
python -m ruff format custom_components/abode_security
python -m ruff check custom_components/abode_security

# Type checking
python -m mypy custom_components/abode_security --ignore-missing-imports

# Quick smoke test in Home Assistant (if available)
# Reload integration and check logs
```

---

## Commit Strategy for Phase 1.5

After each completed task:

```bash
# Error handling decorator
git add custom_components/abode_security/decorators.py custom_components/abode_security/
git commit -m "refactor: Extract error handling to decorator

- Create decorators.py with handle_abode_errors decorator
- Apply to error-prone methods in switch.py and alarm_control_panel.py
- Reduce boilerplate exception handling code
- Centralize error logging behavior"

# Service handler factory
git add custom_components/abode_security/services.py
git commit -m "refactor: Consolidate service handlers with factory

- Create _create_service_handler factory function
- Consolidate 5 service handlers into reusable factory
- Reduce services.py from ~200 to ~120 lines
- Single source of truth for service behavior"

# Event callback helpers
git add custom_components/abode_security/switch.py
git commit -m "refactor: Extract event callback helpers

- Create _subscribe_to_events and _unsubscribe_from_events methods
- Better error handling for optional remove_event_callback
- Cleaner async_added_to_hass and async_will_remove_from_hass
- Easier to test event lifecycle"

# Test constants
git add tests/test_constants.py tests/
git commit -m "refactor: Centralize test constants

- Create test_constants.py with shared fixtures
- Update all test_*.py files to use centralized constants
- Reduce duplication across test suite
- Single source of truth for fixture IDs"

# Lifecycle tests
git add tests/test_entity_lifecycle.py
git commit -m "test: Add entity lifecycle and error handling tests

- Test entity initialization and event subscription
- Test cleanup and event unsubscription
- Test error recovery and fallback behavior
- Improve coverage of edge cases"

# Event code extraction
git add custom_components/abode_security/switch.py
git commit -m "refactor: Extract event code mapping logic

- Create _map_event_code_to_alarm_type helper
- Eliminate duplication in _alarm_event_callback and _alarm_end_callback
- Cleaner event code handling
- Easier to add new event types"
```

---

## Phase 1.5 Success Criteria

✅ All tasks complete when:
- [ ] Decorators module created and applied to error-prone methods
- [ ] Service handlers consolidated with factory pattern
- [ ] Event callback helpers extracted
- [ ] Test constants centralized in test_constants.py
- [ ] New lifecycle and error handling tests added
- [ ] Event code mapping extracted to helper
- [ ] All tests passing
- [ ] Code formatted with ruff
- [ ] Type checking passes (mypy)
- [ ] All commits documented in git log
- [ ] DEVELOPMENT.md updated with Phase 1.5 completion notes

---

## Expected Completion Time

- Decorators: 30 minutes
- Service factory: 30 minutes
- Event helpers: 20 minutes
- Test constants: 15 minutes
- Lifecycle tests: 45 minutes
- Event code extraction: 15 minutes

**Total Phase 1.5 estimate:** 2-2.5 hours

---

## Refactoring Impact Summary

### Code Reduction
- switch.py: ~30 lines saved (event callbacks)
- alarm_control_panel.py: ~40 lines saved (error handling)
- services.py: ~80 lines saved (factory pattern)
- models.py: ~10 lines saved (decorator)
- **Total: ~160 lines of boilerplate eliminated**

### Test Coverage Improvement
- +5-10 new test functions
- Coverage of entity lifecycle events
- Coverage of error recovery paths
- Coverage of missing method fallbacks

### Maintainability
- Single source of truth for error handling
- Single source of truth for service handlers
- Single source of truth for test fixtures
- Centralized event code mapping

---

## Next: Phase 3

After Phase 1.5 is complete, Phase 3 includes:
- Configuration options (disable features conditionally)
- Advanced features from the feature wishlist
- Performance optimizations using async patterns
- Library async conversion planning
