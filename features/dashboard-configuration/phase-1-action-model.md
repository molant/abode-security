---
status: pending
phase: 1
title: Action Model and Storage
---

# Phase 1: Action Model and Storage

## Overview

Create the `AbodeAction` dataclass and `ActionStore` class for persistent storage of action configurations.

## File to Create

`custom_components/abode_security/action_manager.py` (partial - model and store only)

## Sub-Phase A: AbodeAction Dataclass

### Tasks

- [x] Create `AbodeAction` dataclass with all fields:
  - `id: str` - UUID string
  - `name: str` - User-friendly name
  - `modes: list[str]` - List of modes ["standby", "home", "away"]
  - `sensor_entity_ids: list[str]` - HA binary sensor entity IDs
  - `alarm_entity_ids: list[str]` - Abode alarm switch entity IDs
  - `enabled: bool = True` - Whether action is active
  - `delay_seconds: int = 0` - Delay before triggering (0-60)
  - `last_triggered: datetime | None = None` - Last trigger timestamp
  - `trigger_count: int = 0` - Number of times triggered

- [x] Implement `to_dict()` method for JSON serialization
  - Convert datetime to ISO format string or None

- [x] Implement `from_dict()` classmethod for deserialization
  - Parse ISO format string back to datetime

### Test Specification

**File:** `tests/test_action_manager.py`

```python
# Test: AbodeAction creation with defaults
def test_action_creation_defaults():
    action = AbodeAction(
        id="uuid-1",
        name="Test Action",
        modes=["home"],
        sensor_entity_ids=["binary_sensor.door"],
        alarm_entity_ids=["switch.panic_alarm"],
    )
    assert action.enabled == True
    assert action.delay_seconds == 0
    assert action.last_triggered is None
    assert action.trigger_count == 0

# Test: AbodeAction serialization to dict
def test_action_to_dict():
    action = AbodeAction(...)
    d = action.to_dict()
    assert d["id"] == action.id
    assert d["name"] == action.name
    assert isinstance(d["modes"], list)

# Test: AbodeAction serialization with datetime
def test_action_to_dict_with_datetime():
    action = AbodeAction(..., last_triggered=datetime.now(UTC))
    d = action.to_dict()
    assert isinstance(d["last_triggered"], str)  # ISO format

# Test: AbodeAction deserialization from dict
def test_action_from_dict():
    d = {"id": "uuid-1", "name": "Test", ...}
    action = AbodeAction.from_dict(d)
    assert action.id == "uuid-1"

# Test: AbodeAction round-trip (to_dict then from_dict)
def test_action_round_trip():
    original = AbodeAction(...)
    restored = AbodeAction.from_dict(original.to_dict())
    assert original == restored
```

---

## Sub-Phase B: ActionStore Class

### Tasks

- [ ] Create `ActionStore` class using Home Assistant's `Store` API
  - Storage file: `.storage/abode_security_actions.json`
  - Store version: 1

- [ ] Implement `async_load()` method
  - Load actions from storage
  - Handle missing file (return empty dict)
  - Deserialize each action using `AbodeAction.from_dict()`

- [ ] Implement `async_save()` method
  - Serialize all actions using `to_dict()`
  - Write to storage file

- [ ] Implement `async_add(action: AbodeAction)` method
  - Add action to internal dict
  - Call `async_save()`

- [ ] Implement `async_remove(action_id: str)` method
  - Remove action from internal dict
  - Call `async_save()`
  - Return True if removed, False if not found

- [ ] Implement `get(action_id: str)` method (sync, from cache)

- [ ] Implement `get_all()` method (sync, returns list)

### Test Specification

```python
# Test: ActionStore initialization
async def test_store_init(hass):
    store = ActionStore(hass)
    await store.async_load()
    assert store.get_all() == []

# Test: ActionStore add and retrieve
async def test_store_add_and_get(hass):
    store = ActionStore(hass)
    await store.async_load()
    action = AbodeAction(...)
    await store.async_add(action)
    assert store.get(action.id) == action

# Test: ActionStore persistence (reload)
async def test_store_persistence(hass):
    store1 = ActionStore(hass)
    await store1.async_load()
    await store1.async_add(AbodeAction(id="test-1", ...))

    store2 = ActionStore(hass)
    await store2.async_load()
    assert store2.get("test-1") is not None

# Test: ActionStore remove
async def test_store_remove(hass):
    store = ActionStore(hass)
    await store.async_load()
    await store.async_add(AbodeAction(id="test-1", ...))
    result = await store.async_remove("test-1")
    assert result == True
    assert store.get("test-1") is None

# Test: ActionStore remove non-existent
async def test_store_remove_not_found(hass):
    store = ActionStore(hass)
    await store.async_load()
    result = await store.async_remove("non-existent")
    assert result == False

# Test: ActionStore get_all returns list
async def test_store_get_all(hass):
    store = ActionStore(hass)
    await store.async_load()
    await store.async_add(AbodeAction(id="1", ...))
    await store.async_add(AbodeAction(id="2", ...))
    all_actions = store.get_all()
    assert len(all_actions) == 2
    assert isinstance(all_actions, list)
```

---

## Verification

```bash
# Run phase 1 tests
pytest tests/test_action_manager.py -v -k "action_creation or action_to_dict or action_from_dict or action_round_trip or store"

# Expected: All tests pass
```

## Notes

- Use `homeassistant.helpers.storage.Store` for persistence
- Store data format:
  ```json
  {
    "version": 1,
    "data": {
      "actions": {
        "uuid-1": { ... action dict ... },
        "uuid-2": { ... action dict ... }
      }
    }
  }
  ```
- datetime fields use UTC timezone
