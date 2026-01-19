---
status: complete
phase: 4
title: Action Trigger Coordinator
---

# Phase 4: Action Trigger Coordinator

## Overview

Create the `ActionTriggerCoordinator` that listens to Home Assistant state changes and triggers matching actions when binary sensors activate.

## File to Create

`custom_components/abode_security/action_trigger.py`

## Sub-Phase A: Coordinator Core

### Tasks

- [x] Create `ActionTriggerCoordinator` class
  - Constructor takes `hass: HomeAssistant, action_manager: ActionManager`
  - Store reference to debounce config (from `hass.data[DOMAIN]`)

- [x] Implement `async_start()` method
  - Subscribe to `EVENT_STATE_CHANGED` events
  - Store unsubscribe callback for cleanup

- [x] Implement `async_stop()` method
  - Unsubscribe from events
  - Cancel any pending delayed triggers

- [x] Implement `_get_current_mode()` helper
  - Find `alarm_control_panel.abode_*` entity
  - Map HA state to mode:
    - `disarmed` → `"standby"`
    - `armed_home` → `"home"`
    - `armed_away` → `"away"`
  - Return `None` if no alarm panel found

### Test Specification

**File:** `tests/test_action_trigger.py`

```python
# Test: Coordinator initialization
async def test_coordinator_init(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    assert coordinator is not None

# Test: Start and stop
async def test_coordinator_start_stop(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()
    # Should not raise
    await coordinator.async_stop()

# Test: Get current mode - standby
async def test_coordinator_get_mode_standby(hass, action_manager):
    hass.states.async_set("alarm_control_panel.abode_alarm", "disarmed")
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    mode = coordinator._get_current_mode()
    assert mode == "standby"

# Test: Get current mode - home
async def test_coordinator_get_mode_home(hass, action_manager):
    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    mode = coordinator._get_current_mode()
    assert mode == "home"

# Test: Get current mode - away
async def test_coordinator_get_mode_away(hass, action_manager):
    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    mode = coordinator._get_current_mode()
    assert mode == "away"

# Test: Get current mode - no alarm panel
async def test_coordinator_get_mode_no_panel(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    mode = coordinator._get_current_mode()
    assert mode is None
```

---

## Sub-Phase B: State Change Handling

### Tasks

- [x] Implement `_handle_state_change(event: Event)` callback
  - Extract entity_id from event
  - Filter: only process `binary_sensor.*` entities
  - Filter: only process transitions to state `"on"`
  - Call `_process_sensor_activation(entity_id)`

- [x] Implement `_process_sensor_activation(entity_id: str)` method
  - Get current mode
  - If mode is None, log warning and return
  - Query `action_manager.async_get_by_mode(mode)`
  - Filter actions: entity_id must be in action's `sensor_entity_ids`
  - For each matching action, call `_trigger_action(action, entity_id)`

- [x] Implement debouncing logic
  - Track last trigger time per (action_id, sensor_id) pair
  - Skip trigger if within debounce window
  - Use `hass.data[DOMAIN]["config"]["debounce_seconds"]`

### Test Specification

```python
# Test: Ignore non-binary-sensor entities
async def test_coordinator_ignores_non_binary_sensor(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    # Create action
    action = await action_manager.async_create(
        name="Test",
        modes=["home"],
        sensor_entity_ids=["switch.test"],  # Not a binary_sensor
        alarm_entity_ids=["switch.panic_alarm"],
    )

    # Set alarm mode
    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

    # Trigger switch state change
    hass.states.async_set("switch.test", "on")
    await hass.async_block_till_done()

    # Action should NOT have been triggered
    updated = await action_manager.async_get(action.id)
    assert updated.trigger_count == 0

# Test: Ignore transitions to "off"
async def test_coordinator_ignores_off_state(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        name="Test",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.panic_alarm"],
    )

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "on")

    # Trigger off state
    hass.states.async_set("binary_sensor.door", "off")
    await hass.async_block_till_done()

    # Should not increment trigger (we'd need to track this separately)
    # This test verifies no error occurs

# Test: Match sensor and mode
async def test_coordinator_matches_sensor_and_mode(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        name="Door Alert",
        modes=["away"],
        sensor_entity_ids=["binary_sensor.front_door"],
        alarm_entity_ids=["switch.panic_alarm"],
    )

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_away")

    # Initial state
    hass.states.async_set("binary_sensor.front_door", "off")
    await hass.async_block_till_done()

    # Trigger sensor
    hass.states.async_set("binary_sensor.front_door", "on")
    await hass.async_block_till_done()

    updated = await action_manager.async_get(action.id)
    assert updated.trigger_count == 1

# Test: No match if wrong mode
async def test_coordinator_no_match_wrong_mode(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        name="Away Only",
        modes=["away"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.panic_alarm"],
    )

    # Set to HOME mode, not away
    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    updated = await action_manager.async_get(action.id)
    assert updated.trigger_count == 0

# Test: No match if wrong sensor
async def test_coordinator_no_match_wrong_sensor(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        name="Motion Only",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.motion"],
        alarm_entity_ids=["switch.panic_alarm"],
    )

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

    # Trigger different sensor
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    updated = await action_manager.async_get(action.id)
    assert updated.trigger_count == 0

# Test: Debouncing prevents rapid triggers
async def test_coordinator_debounce(hass, action_manager):
    hass.data[DOMAIN] = {"config": {"debounce_seconds": 1.0}}

    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(...)

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

    # Rapid triggers
    for _ in range(5):
        hass.states.async_set("binary_sensor.door", "off")
        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

    # Should only trigger once due to debounce
    updated = await action_manager.async_get(action.id)
    assert updated.trigger_count == 1
```

---

## Sub-Phase C: Action Execution

### Tasks

- [x] Implement `_trigger_action(action: AbodeAction, triggered_by: str)` method
  - If action has `delay_seconds > 0`, schedule delayed execution
  - Otherwise, execute immediately via `_execute_action()`

- [x] Implement `_execute_action(action: AbodeAction, triggered_by: str)` method
  - For each alarm in `action.alarm_entity_ids`:
    - Try to call `hass.services.async_call("switch", "turn_on", {"entity_id": alarm})`
    - On failure: log error, continue to next alarm (don't abort)
    - Track which alarms succeeded/failed
  - Record trigger: `action_manager.async_record_trigger(action.id)`
  - Fire HA event with success/failure info:
    ```python
    hass.bus.async_fire("abode_security.action_triggered", {
        ...
        "alarms_triggered": [successful_alarm_ids],
        "alarms_failed": [failed_alarm_ids],  # empty if all succeeded
    })
    ```
  - Log errors at WARNING level: `_LOGGER.warning("Failed to trigger alarm %s: %s", alarm_id, error)`

- [x] Implement delayed execution with cancellation support
  - Use `asyncio.create_task()` with sleep
  - Track pending tasks in `_pending_delays: dict[str, asyncio.Task]` keyed by `f"{action_id}:{sensor_id}"`
  - Cancel task if action is disabled/deleted before delay completes
  - Provide `cancel_pending_for_action(action_id: str)` method for ActionManager to call on delete/disable
  - Clean up completed tasks from tracking dict

- [x] Event data structure:
  ```python
  {
      "action_id": action.id,
      "action_name": action.name,
      "triggered_by": triggered_by,  # sensor entity_id
      "mode": current_mode,
      "alarms_triggered": [successful_alarm_ids],
      "alarms_failed": [failed_alarm_ids],
      "timestamp": datetime.now(UTC).isoformat(),
  }
  ```

### Test Specification

```python
# Test: Trigger calls alarm service
async def test_coordinator_triggers_alarm_service(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        name="Test",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.panic_alarm"],
    )

    # Mock service call
    service_calls = []
    async def mock_service(call):
        service_calls.append(call)
    hass.services.async_register("switch", "turn_on", mock_service)

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    assert len(service_calls) == 1
    assert service_calls[0].data["entity_id"] == "switch.panic_alarm"

# Test: Trigger fires HA event
async def test_coordinator_fires_event(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(...)

    events = []
    hass.bus.async_listen("abode_security.action_triggered", lambda e: events.append(e))

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["action_id"] == action.id
    assert events[0].data["triggered_by"] == "binary_sensor.door"
    assert events[0].data["mode"] == "home"

# Test: Multiple actions same sensor
async def test_coordinator_multiple_actions(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action1 = await action_manager.async_create(
        name="Action 1",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.panic_alarm"],
    )
    action2 = await action_manager.async_create(
        name="Action 2",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.medical_alarm"],
    )

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    updated1 = await action_manager.async_get(action1.id)
    updated2 = await action_manager.async_get(action2.id)
    assert updated1.trigger_count == 1
    assert updated2.trigger_count == 1

# Test: Disabled action not triggered
async def test_coordinator_disabled_action_not_triggered(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(...)
    await action_manager.async_update(action.id, enabled=False)

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    updated = await action_manager.async_get(action.id)
    assert updated.trigger_count == 0

# Test: Delayed action
async def test_coordinator_delayed_action(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        ...,
        delay_seconds=1,
    )

    service_calls = []
    async def mock_service(call):
        service_calls.append(call)
    hass.services.async_register("switch", "turn_on", mock_service)

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    # Not triggered yet
    assert len(service_calls) == 0

    # Wait for delay
    await asyncio.sleep(1.1)
    await hass.async_block_till_done()

    assert len(service_calls) == 1

# Test: Delayed action cancelled on action delete
async def test_coordinator_delayed_action_cancelled_on_delete(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        ...,
        delay_seconds=2,
    )

    service_calls = []
    async def mock_service(call):
        service_calls.append(call)
    hass.services.async_register("switch", "turn_on", mock_service)

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    # Delete action before delay completes
    await action_manager.async_delete(action.id)

    # Wait past delay
    await asyncio.sleep(2.1)
    await hass.async_block_till_done()

    # Should NOT have triggered
    assert len(service_calls) == 0

# Test: Delayed action cancelled on action disable
async def test_coordinator_delayed_action_cancelled_on_disable(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(..., delay_seconds=2)

    service_calls = []
    async def mock_service(call):
        service_calls.append(call)
    hass.services.async_register("switch", "turn_on", mock_service)

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    # Disable action before delay completes
    await action_manager.async_update(action.id, enabled=False)

    # Wait past delay
    await asyncio.sleep(2.1)
    await hass.async_block_till_done()

    # Should NOT have triggered
    assert len(service_calls) == 0

# Test: Multi-alarm continues on failure
async def test_coordinator_multi_alarm_continues_on_failure(hass, action_manager):
    coordinator = ActionTriggerCoordinator(hass, action_manager)
    await coordinator.async_start()

    action = await action_manager.async_create(
        name="Test",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.panic_alarm", "switch.medical_alarm"],
    )

    service_calls = []
    call_count = 0
    async def mock_service(call):
        nonlocal call_count
        call_count += 1
        if call.data["entity_id"] == "switch.panic_alarm":
            raise Exception("Service failed")
        service_calls.append(call)
    hass.services.async_register("switch", "turn_on", mock_service)

    events = []
    hass.bus.async_listen("abode_security.action_triggered", lambda e: events.append(e))

    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")
    hass.states.async_set("binary_sensor.door", "off")
    hass.states.async_set("binary_sensor.door", "on")
    await hass.async_block_till_done()

    # Both were attempted
    assert call_count == 2
    # One succeeded
    assert len(service_calls) == 1
    # Event includes failure info
    assert len(events) == 1
    assert "switch.medical_alarm" in events[0].data["alarms_triggered"]
    assert "switch.panic_alarm" in events[0].data["alarms_failed"]
```

---

## Sub-Phase D: Integration

### Tasks

- [x] Modify `__init__.py` `async_setup_entry()`:
  - Create `ActionTriggerCoordinator` with references to `ActionManager`
  - Call `coordinator.async_start()`
  - Store in `hass.data[DOMAIN]["action_trigger"]`
  - Wire up coordinator to ActionManager for cancellation callbacks:
    ```python
    action_manager.set_trigger_coordinator(coordinator)
    ```

- [x] Modify `__init__.py` `async_unload_entry()`:
  - Call `coordinator.async_stop()` (cancels all pending delays)
  - Remove from `hass.data[DOMAIN]`

- [x] Wire up ActionManager delete/disable to cancel pending delays:
  ```python
  # In ActionManager.async_delete():
  if self._trigger_coordinator:
      self._trigger_coordinator.cancel_pending_for_action(action_id)

  # In ActionManager.async_update() when enabled changes to False:
  if self._trigger_coordinator and not updated.enabled:
      self._trigger_coordinator.cancel_pending_for_action(action_id)
  ```

### Code Changes in `__init__.py`

```python
# In async_setup_entry() - after action_manager setup:
from .action_trigger import ActionTriggerCoordinator

coordinator = ActionTriggerCoordinator(hass, action_manager)
action_manager.set_trigger_coordinator(coordinator)
await coordinator.async_start()
hass.data[DOMAIN]["action_trigger"] = coordinator

# In async_unload_entry():
if coordinator := hass.data[DOMAIN].get("action_trigger"):
    await coordinator.async_stop()
hass.data[DOMAIN].pop("action_trigger", None)
```

---

## Verification

```bash
# Run action trigger tests
pytest tests/test_action_trigger.py -v

# Integration test with dev environment
./scripts/dev.sh

# Create an action via WebSocket, then trigger a sensor
# Check HA events and alarm state changes
```

## Notes

- Use `async_track_state_change_event` from `homeassistant.helpers.event` for cleaner event subscription
- Log all trigger events at INFO level for debugging
- Handle exceptions gracefully in event handlers to prevent breaking HA event loop
- Consider using `hass.async_create_task()` for delayed execution
