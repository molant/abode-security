---
status: pending
phase: 2
title: Action Manager CRUD
---

# Phase 2: Action Manager CRUD

## Overview

Create the `ActionManager` class with CRUD operations and validation logic. This builds on Phase 1's `AbodeAction` and `ActionStore`.

## File to Modify

`custom_components/abode_security/action_manager.py` (add ActionManager class)

## Sub-Phase A: ActionManager Core

### Tasks

- [x] Create `ActionManager` class
  - Constructor takes `hass: HomeAssistant`
  - Initialize `ActionStore` internally
  - Add `async_setup()` method to load store

- [x] Implement `async_create(name, modes, sensor_entity_ids, alarm_entity_ids, delay_seconds=0)` method
  - Generate UUID for new action
  - Create `AbodeAction` instance
  - Validate before saving (see validation rules below)
  - Add to store
  - Return created action

- [x] Implement `async_get(action_id: str)` method
  - Return action or None if not found

- [x] Implement `async_get_all()` method
  - Return list of all actions

- [x] Implement `async_update(action_id, **kwargs)` method
  - Update specified fields only
  - Validate after applying changes
  - Save to store
  - Return updated action or None if not found

- [x] Implement `async_delete(action_id: str)` method
  - Remove from store
  - Return True if deleted, False if not found

### Validation Rules

Raise `ValueError` with descriptive message if:
- `name` is empty or whitespace only
- `name` exceeds 100 characters
- `modes` is empty or contains invalid mode (not in ["standby", "home", "away"])
- `sensor_entity_ids` is empty
- `alarm_entity_ids` is empty
- `delay_seconds` is not 0-60

### Entity Existence Warnings

The manager should **warn** (not block) if entities don't exist:
- Check if each `sensor_entity_id` exists in `hass.states`
- Check if each `alarm_entity_id` exists in `hass.states`
- Log warning: `_LOGGER.warning("Entity %s not found, action may not trigger correctly", entity_id)`
- Return warnings in create/update response for frontend display

This allows creating actions before all entities are available (e.g., during setup).

### Test Specification

```python
# Test: Create action with valid data
async def test_manager_create_valid(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(
        name="Motion Alert",
        modes=["away"],
        sensor_entity_ids=["binary_sensor.motion"],
        alarm_entity_ids=["switch.panic_alarm"],
    )
    assert action.id is not None
    assert action.name == "Motion Alert"
    assert action.enabled == True

# Test: Create action validation - empty name
async def test_manager_create_empty_name(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="name"):
        await manager.async_create(name="", modes=["home"], ...)

# Test: Create action validation - whitespace name
async def test_manager_create_whitespace_name(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="name"):
        await manager.async_create(name="   ", modes=["home"], ...)

# Test: Create action validation - empty modes
async def test_manager_create_empty_modes(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="mode"):
        await manager.async_create(name="Test", modes=[], ...)

# Test: Create action validation - invalid mode
async def test_manager_create_invalid_mode(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="mode"):
        await manager.async_create(name="Test", modes=["invalid"], ...)

# Test: Create action validation - empty sensors
async def test_manager_create_empty_sensors(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="sensor"):
        await manager.async_create(name="Test", sensor_entity_ids=[], ...)

# Test: Create action validation - empty alarms
async def test_manager_create_empty_alarms(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="alarm"):
        await manager.async_create(name="Test", alarm_entity_ids=[], ...)

# Test: Create action validation - invalid delay
async def test_manager_create_invalid_delay(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="delay"):
        await manager.async_create(..., delay_seconds=100)

# Test: Create action validation - name too long
async def test_manager_create_name_too_long(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    with pytest.raises(ValueError, match="name"):
        await manager.async_create(name="x" * 101, modes=["home"], ...)

# Test: Create action with missing entity logs warning
async def test_manager_create_missing_entity_warning(hass, caplog):
    manager = ActionManager(hass)
    await manager.async_setup()
    # Entity doesn't exist in hass.states
    action = await manager.async_create(
        name="Test",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.nonexistent"],
        alarm_entity_ids=["switch.panic_alarm"],
    )
    # Should succeed but log warning
    assert action is not None
    assert "not found" in caplog.text

# Test: Get action by ID
async def test_manager_get(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    created = await manager.async_create(...)
    retrieved = await manager.async_get(created.id)
    assert retrieved == created

# Test: Get action not found
async def test_manager_get_not_found(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    result = await manager.async_get("non-existent")
    assert result is None

# Test: Get all actions
async def test_manager_get_all(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    await manager.async_create(name="Action 1", ...)
    await manager.async_create(name="Action 2", ...)
    all_actions = await manager.async_get_all()
    assert len(all_actions) == 2

# Test: Update action
async def test_manager_update(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(name="Original", ...)
    updated = await manager.async_update(action.id, name="Updated")
    assert updated.name == "Updated"
    assert updated.id == action.id

# Test: Update action partial
async def test_manager_update_partial(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(name="Test", modes=["home"], ...)
    updated = await manager.async_update(action.id, modes=["home", "away"])
    assert updated.name == "Test"  # unchanged
    assert updated.modes == ["home", "away"]

# Test: Update action not found
async def test_manager_update_not_found(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    result = await manager.async_update("non-existent", name="New")
    assert result is None

# Test: Update action with validation error
async def test_manager_update_validation_error(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(name="Test", ...)
    with pytest.raises(ValueError):
        await manager.async_update(action.id, name="")

# Test: Delete action
async def test_manager_delete(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(...)
    result = await manager.async_delete(action.id)
    assert result == True
    assert await manager.async_get(action.id) is None

# Test: Delete action not found
async def test_manager_delete_not_found(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    result = await manager.async_delete("non-existent")
    assert result == False
```

---

## Sub-Phase B: ActionManager Helpers

### Tasks

- [ ] Implement `async_get_by_mode(mode: str)` method
  - Return list of enabled actions that include the given mode

- [ ] Implement `async_get_enabled()` method
  - Return list of all enabled actions

- [ ] Implement `async_toggle(action_id: str)` method
  - Toggle the `enabled` field
  - Return updated action or None

- [ ] Implement `async_record_trigger(action_id: str)` method
  - Update `last_triggered` to current datetime (UTC)
  - Increment `trigger_count`
  - Save to store

### Test Specification

```python
# Test: Get actions by mode
async def test_manager_get_by_mode(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    await manager.async_create(name="Home Action", modes=["home"], ...)
    await manager.async_create(name="Away Action", modes=["away"], ...)
    await manager.async_create(name="Both Action", modes=["home", "away"], ...)

    home_actions = await manager.async_get_by_mode("home")
    assert len(home_actions) == 2

    away_actions = await manager.async_get_by_mode("away")
    assert len(away_actions) == 2

# Test: Get by mode excludes disabled
async def test_manager_get_by_mode_excludes_disabled(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(name="Test", modes=["home"], ...)
    await manager.async_update(action.id, enabled=False)

    home_actions = await manager.async_get_by_mode("home")
    assert len(home_actions) == 0

# Test: Get enabled actions
async def test_manager_get_enabled(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    await manager.async_create(name="Enabled", ...)
    action2 = await manager.async_create(name="To Disable", ...)
    await manager.async_update(action2.id, enabled=False)

    enabled = await manager.async_get_enabled()
    assert len(enabled) == 1
    assert enabled[0].name == "Enabled"

# Test: Toggle action
async def test_manager_toggle(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(name="Test", ...)
    assert action.enabled == True

    toggled = await manager.async_toggle(action.id)
    assert toggled.enabled == False

    toggled_again = await manager.async_toggle(action.id)
    assert toggled_again.enabled == True

# Test: Toggle action not found
async def test_manager_toggle_not_found(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    result = await manager.async_toggle("non-existent")
    assert result is None

# Test: Record trigger
async def test_manager_record_trigger(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(...)
    assert action.last_triggered is None
    assert action.trigger_count == 0

    await manager.async_record_trigger(action.id)

    updated = await manager.async_get(action.id)
    assert updated.last_triggered is not None
    assert updated.trigger_count == 1

# Test: Record trigger increments count
async def test_manager_record_trigger_increments(hass):
    manager = ActionManager(hass)
    await manager.async_setup()
    action = await manager.async_create(...)

    await manager.async_record_trigger(action.id)
    await manager.async_record_trigger(action.id)
    await manager.async_record_trigger(action.id)

    updated = await manager.async_get(action.id)
    assert updated.trigger_count == 3
```

---

## Verification

```bash
# Run all Phase 2 tests
pytest tests/test_action_manager.py -v

# Expected: All tests pass (Phase 1 + Phase 2 tests)
```

## Notes

- All async methods should be properly typed with return annotations
- Use `uuid.uuid4()` for generating action IDs
- Validation should happen before any state changes
- The `async_record_trigger` method will be called by ActionTriggerCoordinator in Phase 4
