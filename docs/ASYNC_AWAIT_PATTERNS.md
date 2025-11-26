# Async/Await Patterns in Abode Security Integration

## Overview

This document outlines the async/await patterns used in the Abode Security Home Assistant integration, including design decisions and rationale to prevent future misidentification during code reviews.

## Service Handler Pattern

### Key Principle

**A service handler should be async if and only if it performs I/O operations (awaits) that must complete before returning.**

### Decision Rule

```
Does the handler contain any await statements?
├── YES → Must be async def
└── NO → Should be def (sync)
```

## Service Handlers in This Integration

### Sync Handlers (No I/O)

#### `_capture_image`

**Location:** `custom_components/abode_security/services.py:115`

```python
def _capture_image(call: ServiceCall) -> None:
    """Capture a new image.

    This is a sync function (not async) because it only sends dispatcher signals
    via dispatcher_send(), which is a pure synchronous operation with no I/O.
    """
    # Only calls dispatcher_send() - pure sync, no I/O
```

**Rationale:**
- `dispatcher_send()` is a fire-and-forget signal broadcast
- No network I/O, no async operations required
- Handler returns immediately after queuing signals
- Making it async would add unnecessary coroutine overhead

#### `_trigger_automation`

**Location:** `custom_components/abode_security/services.py:135`

```python
def _trigger_automation(call: ServiceCall) -> None:
    """Trigger an Abode automation.

    This is a sync function (not async) because it only sends dispatcher signals
    via dispatcher_send(), which is a pure synchronous operation with no I/O.
    """
    # Only calls dispatcher_send() - pure sync, no I/O
```

**Rationale:**
- Same as `_capture_image` - only dispatcher signaling
- Pure synchronous operation with no awaits
- Fire-and-forget pattern, no need for async overhead

### Async Handlers (Perform I/O)

#### `_change_setting`

**Location:** `custom_components/abode_security/services.py:99`

```python
async def _change_setting(call: ServiceCall) -> None:
    """Change an Abode system setting."""
    try:
        await abode_system.abode.set_setting(setting, value)  # ← I/O
```

**Rationale:**
- Contains `await abode.set_setting()` - performs network I/O
- Must wait for API response before returning
- Cannot be a sync function calling async method
- Correct: async def with await

#### `_trigger_alarm_handler`

**Location:** `custom_components/abode_security/services.py:155`

```python
async def _trigger_alarm_handler(call: ServiceCall) -> None:
    """Trigger a manual alarm."""
    try:
        alarm = abode_system.abode.get_alarm()
        await alarm.trigger_manual_alarm(alarm_type)  # ← I/O
```

**Rationale:**
- Contains `await alarm.trigger_manual_alarm()` - performs network I/O
- Must wait for API response before returning
- Correct: async def with await

#### Handler Factory

**Location:** `custom_components/abode_security/services.py:73`

```python
async def handler(call: ServiceCall) -> None:
    # ...
    await method(*args)  # ← I/O
```

**Rationale:**
- Created by `_create_service_handler()` factory
- Contains dynamic await calls via `await method(*args)`
- Correct: async def with await

## Home Assistant Service Registration

Home Assistant's `async_register()` accepts **both sync and async handlers**:

```python
hass.services.async_register(
    DOMAIN, SERVICE_CAPTURE_IMAGE, _capture_image,  # ← Can be sync
    schema=CAPTURE_IMAGE_SCHEMA
)

hass.services.async_register(
    DOMAIN, SERVICE_TRIGGER_ALARM, _trigger_alarm_handler,  # ← Must be async
    schema=TRIGGER_ALARM_SCHEMA
)
```

The service dispatcher automatically handles both correctly:
- **Sync handlers:** Called directly, returns immediately
- **Async handlers:** Awaited by the service dispatcher

## Timeout Pattern

All `async_add_executor_job()` calls are protected with `asyncio.wait_for()`:

```python
try:
    await asyncio.wait_for(
        self.hass.async_add_executor_job(
            self._data.abode.events.add_connection_status_callback,
            self.unique_id,
            self._update_connection_status,
        ),
        timeout=10.0,  # ← 10-second timeout
    )
except asyncio.TimeoutError:
    pass  # ← Non-critical, ignore timeout gracefully
```

**Rationale:**
- Prevents event loop blocking if callback registration hangs
- 10 seconds is reasonable for executor thread pool operations
- Non-critical operations gracefully degrade on timeout
- Entity continues to function with polling if callback fails

## Naming Conventions

### Async Functions

All async functions follow Home Assistant naming conventions:

- **Service platform methods:** `async_turn_on()`, `async_turn_off()`, `async_lock()`, etc.
- **Entity lifecycle:** `async_added_to_hass()`, `async_will_remove_from_hass()`, `async_update()`
- **Config flow:** `async_step_user()`, `async_step_mfa()`, etc.
- **Setup functions:** `async_setup()`, `async_setup_entry()`

### Exception

**Service handlers do NOT need the `async_` prefix** because they're handler functions, not entity/platform methods:
- `_change_setting` (async handler)
- `_capture_image` (sync handler)
- `_trigger_automation` (sync handler)

## Performance Impact

### Unnecessary Async Overhead

Making a sync function async adds overhead:
- Creates coroutine object
- Requires event loop scheduling
- Adds context switching cost
- No benefit if no await is performed

Example: `_capture_image` as async (INEFFICIENT):
```python
async def _capture_image(call: ServiceCall) -> None:
    # Only calls dispatcher_send() - no await
    # Coroutine object created and scheduled for no benefit
    dispatcher_send(call.hass, signal)
```

Example: `_capture_image` as sync (EFFICIENT):
```python
def _capture_image(call: ServiceCall) -> None:
    # Called directly, returns immediately
    # No coroutine overhead
    dispatcher_send(call.hass, signal)
```

## Summary Table

| Function | Location | Type | I/O | Reason |
|----------|----------|------|-----|--------|
| `_capture_image` | services.py:115 | sync | No | dispatcher_send only |
| `_trigger_automation` | services.py:135 | sync | No | dispatcher_send only |
| `_change_setting` | services.py:99 | async | Yes | await abode.set_setting |
| `_trigger_alarm_handler` | services.py:155 | async | Yes | await alarm.trigger_manual_alarm |
| handler (factory) | services.py:73 | async | Yes | await method(*args) |

## Code Review Guidelines

When reviewing service handlers or async functions:

1. **Check for await statements**
   - Present → Must be async def
   - Absent → Should be def (sync)

2. **Check for I/O operations**
   - Performs I/O → Must be async def
   - No I/O → Can be sync

3. **Check for fire-and-forget patterns**
   - dispatcher_send, hass.bus.fire, etc. → Should be sync
   - API calls, device operations → Should be async

4. **Look for docstring clarifications**
   - If rationale is explained in docstring → Trust the design
   - If unclear → Ask or investigate further

## Related Issues

**GitHub/Git References:**
- Commit `8e464f4e6efd`: Converted sync dispatcher handlers to sync functions
- Commit `7b7e8d4b30ea`: Added docstring clarifications

**Code Review Date:** 2025-11-25

---

For questions or clarifications on async/await patterns, refer to this document or consult the Home Assistant async documentation at https://developers.home-assistant.io/
