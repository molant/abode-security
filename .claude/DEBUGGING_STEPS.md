# Test Mode Initialization Debugging Guide

## Issue
Test mode switch shows as OFF in Home Assistant UI, but is actually ENABLED in Abode's website.

## Root Cause Analysis
The `async_added_to_hass()` method should fetch the initial status from Abode API when the entity is added to Home Assistant. If this isn't working, the state stays at the default `False`.

## Potential Issues & Fixes Applied

### Issue 1: Polling Timing (FIXED)
**Problem:** Polling might start before `async_added_to_hass()` completes, overwriting the initial status with False.

**Fix Applied:**
- Changed `_attr_should_poll = False` in `__init__` (was `True`)
- Added `_initial_sync_done` flag to track first successful fetch
- Polling is only enabled AFTER the first successful `get_test_mode()` call
- This ensures initial status is set before any polling occurs

### Issue 2: Exception Handling (IMPROVED)
**Problem:** Exceptions in `get_test_mode()` might be silently caught and return False.

**Improvements:**
- Added detailed traceback logging for all exceptions
- Changed warnings from `debug` to `warning` level for visibility
- Added type logging to see what's being returned
- All exceptions are now logged with full details

### Issue 3: Logging Visibility (IMPROVED)
**Problem:** Wasn't clear when/why initialization was failing.

**Improvements:**
- Log when `async_added_to_hass()` is called (INFO level)
- Log when polling starts/happens (DEBUG level)
- Log every API call result
- Log state changes at INFO level for visibility

## How to Debug

### Step 1: Check Home Assistant Logs
Restart Home Assistant and look for these log messages in the Abode Security logs:

1. **Initialization message:**
   ```
   Test mode switch added to Home Assistant, fetching initial status
   ```

2. **Status fetch message:**
   ```
   Initial test mode status fetched: [True/False]
   ```
   - If you see `False` here when test mode is enabled, the API is returning wrong data
   - If you see `True` but UI shows OFF, there's a state persistence issue

3. **Polling enabled message:**
   ```
   Enabling polling after initial sync
   ```

4. **API call details:**
   ```
   get_test_mode() returned: [True/False] (type: <class 'bool'>)
   ```

### Step 2: Check for Exceptions
Look for these error messages:

```
Failed to get test mode status (AbodeException): ...
Unexpected error getting test mode status: ...
get_test_mode method not available in abode client: ...
Failed to get test mode: ...
```

If you see any of these, the traceback will be logged at DEBUG level:
```
Traceback: [full Python traceback]
```

### Step 3: Monitor Polling
After integration is set up, check subsequent polls:

```
Polling test mode status: was [previous], now [current]
```

If this shows `was True, now False` immediately after initialization, polling is overwriting the correct value.

## Expected Flow

**Correct behavior:**
1. Entity created, polling = False
2. async_added_to_hass() called
3. Fetches status from API: "Initial test mode status fetched: True"
4. Polling enabled: "Enabling polling after initial sync"
5. UI shows test mode as ON
6. Subsequent polls show: "Polling test mode status: was True, now True"

**Incorrect behavior (what we're seeing):**
1. Status fetched but UI doesn't show it
2. OR fetch is returning False when API says it's True
3. OR fetch is failing with exception

## Next Steps

1. **Restart Home Assistant container**
2. **Check logs** for the messages above
3. **Share any error messages** that appear
4. If status is still wrong after restart, we'll need to:
   - Check if Abode API endpoint is correct
   - Verify testModeActive field exists in response
   - Test the API directly

## Files Changed This Session

- `custom_components/abode_security/switch.py` - Polling timing and logging
- `custom_components/abode_security/models.py` - Wrapper logging
- `lib/jaraco/abode/event_controller.py` - Added remove_event_callback
