---
status: complete
phase: 3
title: WebSocket API
---

# Phase 3: WebSocket API

## Overview

Create WebSocket API endpoints for the frontend to manage actions, query sensors/alarms, and get mode information.

## Files to Create/Modify

- **Create:** `custom_components/abode_security/websocket_api.py`
- **Create:** `custom_components/abode_security/config_store.py`
- **Modify:** `custom_components/abode_security/__init__.py` (register handlers)

## Implementation Notes (from spec review)

1. **Decorator ordering**: The `@require_admin` decorator must be applied AFTER `@websocket_api.websocket_command` for correct behavior:
   ```python
   @websocket_api.websocket_command({...})
   @require_admin
   @websocket_api.async_response
   async def handler(hass, connection, msg):
   ```

2. **Test fixtures**: `pytest-homeassistant-custom-component` provides `hass_ws_client`. Need to create `action_manager` fixture and verify non-admin client pattern for authorization tests.

3. **Integration setup**: The `__init__.py` already registers a frontend panel. WebSocket commands should be registered in `async_setup()` (before any config entry), while `ActionManager` and `ConfigStore` initialization goes in `async_setup_entry()`.

4. **Test allowlist**: New tests must be added to `enabled_tests` in `conftest.py` to run.

## Security Requirements

All mutation endpoints must:
1. Use `@websocket_api.require_admin` decorator
2. Log operations with user ID for audit trail

```python
from homeassistant.components.websocket_api import require_admin

@require_admin
@websocket_api.websocket_command({...})
@websocket_api.async_response
async def websocket_actions_create(hass, connection, msg):
    # ... create action ...
    _LOGGER.info("Action %s created by user %s", action.id, connection.user.id)
```

Read-only endpoints (list, get, modes, sensors, alarms, config get) do NOT require admin.

---

## Sub-Phase A: Action CRUD Endpoints

### Tasks

- [x] Create `websocket_api.py` with imports and constants

- [x] Implement `websocket_actions_list` handler
  - Command: `abode_security/actions/list`
  - Returns: `{ "actions": [ ... ] }`

- [x] Implement `websocket_actions_get` handler
  - Command: `abode_security/actions/get`
  - Parameters: `action_id: str`
  - Returns: Action dict or error if not found

- [x] Implement `websocket_actions_create` handler
  - Command: `abode_security/actions/create`
  - Parameters: `name, modes, sensor_entity_ids, alarm_entity_ids, delay_seconds (optional)`
  - Returns: Created action dict
  - Errors: `validation_error` with message

- [x] Implement `websocket_actions_update` handler
  - Command: `abode_security/actions/update`
  - Parameters: `action_id, name (optional), modes (optional), ...`
  - Returns: Updated action dict
  - Errors: `not_found` or `validation_error`

- [x] Implement `websocket_actions_delete` handler
  - Command: `abode_security/actions/delete`
  - Parameters: `action_id: str`
  - Returns: `{ "success": true }`
  - Errors: `not_found`

- [x] Implement `websocket_actions_toggle` handler
  - Command: `abode_security/actions/toggle`
  - Parameters: `action_id: str`
  - Toggles the `enabled` field
  - Returns: Updated action dict
  - Requires admin

- [x] Implement `websocket_actions_test` handler
  - Command: `abode_security/actions/test`
  - Parameters: `action_id: str`
  - Manually triggers action (calls alarm services)
  - Returns: `{ "success": true, "alarms_triggered": [...] }`
  - Requires admin
  - Log: `_LOGGER.info("Action %s tested by user %s", action_id, connection.user.id)`

### Test Specification

**File:** `tests/test_websocket_api.py`

```python
# Test: List actions empty
async def test_ws_actions_list_empty(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "abode_security/actions/list"})
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["actions"] == []

# Test: List actions with data
async def test_ws_actions_list_with_data(hass, hass_ws_client, action_manager):
    await action_manager.async_create(name="Test", ...)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "abode_security/actions/list"})
    response = await client.receive_json()
    assert len(response["result"]["actions"]) == 1

# Test: Get action
async def test_ws_actions_get(hass, hass_ws_client, action_manager):
    action = await action_manager.async_create(...)
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/get",
        "action_id": action.id
    })
    response = await client.receive_json()
    assert response["result"]["id"] == action.id

# Test: Get action not found
async def test_ws_actions_get_not_found(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/get",
        "action_id": "non-existent"
    })
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "not_found"

# Test: Create action
async def test_ws_actions_create(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/create",
        "name": "New Action",
        "modes": ["home"],
        "sensor_entity_ids": ["binary_sensor.door"],
        "alarm_entity_ids": ["switch.panic_alarm"],
    })
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["name"] == "New Action"
    assert "id" in response["result"]

# Test: Create action validation error
async def test_ws_actions_create_validation_error(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/create",
        "name": "",  # invalid
        "modes": ["home"],
        "sensor_entity_ids": ["binary_sensor.door"],
        "alarm_entity_ids": ["switch.panic_alarm"],
    })
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "validation_error"

# Test: Update action
async def test_ws_actions_update(hass, hass_ws_client, action_manager):
    action = await action_manager.async_create(name="Original", ...)
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/update",
        "action_id": action.id,
        "name": "Updated"
    })
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["name"] == "Updated"

# Test: Delete action
async def test_ws_actions_delete(hass, hass_ws_client, action_manager):
    action = await action_manager.async_create(...)
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/delete",
        "action_id": action.id
    })
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["success"] == True

# Test: Test action (manual trigger)
async def test_ws_actions_test(hass, hass_ws_client, action_manager):
    action = await action_manager.async_create(...)
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/test",
        "action_id": action.id
    })
    response = await client.receive_json()
    assert response["success"]
    assert "alarms_triggered" in response["result"]

# Test: Toggle action
async def test_ws_actions_toggle(hass, hass_ws_client, action_manager):
    action = await action_manager.async_create(...)
    assert action.enabled == True
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/toggle",
        "action_id": action.id
    })
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["enabled"] == False

# Test: Create action requires admin
async def test_ws_actions_create_requires_admin(hass, hass_ws_client_non_admin):
    client = await hass_ws_client_non_admin(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/create",
        "name": "Test",
        "modes": ["home"],
        "sensor_entity_ids": ["binary_sensor.door"],
        "alarm_entity_ids": ["switch.panic_alarm"],
    })
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"

# Test: Delete action requires admin
async def test_ws_actions_delete_requires_admin(hass, hass_ws_client_non_admin, action_manager):
    action = await action_manager.async_create(...)
    client = await hass_ws_client_non_admin(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/actions/delete",
        "action_id": action.id
    })
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"

# Test: List actions does NOT require admin
async def test_ws_actions_list_no_admin_required(hass, hass_ws_client_non_admin):
    client = await hass_ws_client_non_admin(hass)
    await client.send_json({"id": 1, "type": "abode_security/actions/list"})
    response = await client.receive_json()
    assert response["success"]
```

---

## Sub-Phase B: Entity Query Endpoints

### Tasks

- [x] Implement `websocket_modes_list` handler
  - Command: `abode_security/modes/list`
  - Returns list of modes with metadata:
    ```json
    [
      { "id": "standby", "name": "Standby", "icon": "mdi:lock-open", "action_count": 1, "active": false },
      { "id": "home", "name": "Home", "icon": "mdi:home", "action_count": 3, "active": true },
      { "id": "away", "name": "Away", "icon": "mdi:shield-check", "action_count": 2, "active": false }
    ]
    ```
  - Get active mode from `alarm_control_panel.abode_*` entity state

- [x] Implement `websocket_entities_sensors` handler
  - Command: `abode_security/entities/sensors`
  - Returns ALL HA binary sensors grouped by device_class:
    ```json
    {
      "sensors": {
        "door": [{"entity_id": "...", "name": "...", "state": "..."}],
        "window": [...],
        "motion": [...],
        "moisture": [...],
        "smoke": [...],
        "connectivity": [...],
        "other": [...]
      }
    }
    ```
  - Use `hass.states.async_all()` filtered by `binary_sensor.*`
  - Group by `device_class` attribute

- [x] Implement `websocket_entities_alarms` handler
  - Command: `abode_security/entities/alarms`
  - Returns Abode alarm switches only:
    ```json
    {
      "alarms": [
        { "entity_id": "switch.abode_panic_alarm", "name": "Panic Alarm", "type": "panic" },
        { "entity_id": "switch.abode_medical_alarm", "name": "Medical Alarm", "type": "medical" },
        ...
      ]
    }
    ```
  - Filter by entity_id pattern: `switch.abode_*_alarm` or use entity registry

### Test Specification

```python
# Test: List modes
async def test_ws_modes_list(hass, hass_ws_client):
    # Setup alarm_control_panel entity with state "armed_home"
    hass.states.async_set("alarm_control_panel.abode_alarm", "armed_home")

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "abode_security/modes/list"})
    response = await client.receive_json()

    assert response["success"]
    modes = response["result"]
    assert len(modes) == 3

    home_mode = next(m for m in modes if m["id"] == "home")
    assert home_mode["active"] == True

# Test: List sensors groups by device_class
async def test_ws_entities_sensors(hass, hass_ws_client):
    hass.states.async_set(
        "binary_sensor.front_door",
        "off",
        {"device_class": "door", "friendly_name": "Front Door"}
    )
    hass.states.async_set(
        "binary_sensor.living_room_motion",
        "off",
        {"device_class": "motion", "friendly_name": "Living Room Motion"}
    )

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "abode_security/entities/sensors"})
    response = await client.receive_json()

    assert response["success"]
    sensors = response["result"]["sensors"]
    assert "door" in sensors
    assert "motion" in sensors
    assert len(sensors["door"]) == 1

# Test: List alarms
async def test_ws_entities_alarms(hass, hass_ws_client):
    hass.states.async_set("switch.abode_panic_alarm", "off")
    hass.states.async_set("switch.abode_medical_alarm", "off")

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "abode_security/entities/alarms"})
    response = await client.receive_json()

    assert response["success"]
    alarms = response["result"]["alarms"]
    assert len(alarms) >= 2
```

---

## Sub-Phase C: Config Endpoints

### Config Storage Design

Config is stored in `.storage/abode_security_config.json` and loaded into `hass.data[DOMAIN]["config"]` on startup.

**Flow:**
1. `async_setup_entry()` loads config from storage (or creates defaults)
2. Config is cached in `hass.data[DOMAIN]["config"]`
3. `websocket_config_get` reads from cache
4. `websocket_config_set` updates cache AND persists to storage
5. `ActionTriggerCoordinator` reads debounce from cache

### Tasks

- [x] Create `ConfigStore` class (similar to `ActionStore`)
  - Storage file: `.storage/abode_security_config.json`
  - Default config: `{ "debounce_seconds": 1.0 }`

- [x] Implement `websocket_config_get` handler
  - Command: `abode_security/config/get`
  - Returns: `{ "debounce_seconds": 1.0 }`
  - No admin required

- [x] Implement `websocket_config_set` handler
  - Command: `abode_security/config/set`
  - Parameters: `debounce_seconds: float` (0.1 to 10.0)
  - Updates `hass.data[DOMAIN]["config"]`
  - Persists to storage
  - Returns: Updated config
  - Requires admin

### Test Specification

```python
# Test: Get config
async def test_ws_config_get(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "abode_security/config/get"})
    response = await client.receive_json()
    assert response["success"]
    assert "debounce_seconds" in response["result"]

# Test: Set config
async def test_ws_config_set(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/config/set",
        "debounce_seconds": 2.5
    })
    response = await client.receive_json()
    assert response["success"]
    assert response["result"]["debounce_seconds"] == 2.5

# Test: Set config requires admin
async def test_ws_config_set_requires_admin(hass, hass_ws_client_non_admin):
    client = await hass_ws_client_non_admin(hass)
    await client.send_json({
        "id": 1,
        "type": "abode_security/config/set",
        "debounce_seconds": 2.5
    })
    response = await client.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"

# Test: Config persists across reload
async def test_ws_config_persistence(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    # Set config
    await client.send_json({
        "id": 1,
        "type": "abode_security/config/set",
        "debounce_seconds": 3.0
    })
    await client.receive_json()

    # Verify it's in hass.data
    assert hass.data[DOMAIN]["config"]["debounce_seconds"] == 3.0
```

---

## Sub-Phase D: Integration Setup

### Tasks

- [x] Create `async_register_websocket_commands(hass)` function in `websocket_api.py`

- [x] Modify `__init__.py` `async_setup()` to call `async_register_websocket_commands(hass)`

- [x] Modify `__init__.py` `async_setup_entry()` to:
  - Create and setup `ActionManager`
  - Create and load `ConfigStore`
  - Store in `hass.data[DOMAIN]`

- [x] Add cleanup in `async_unload_entry()`:
  - Remove action_manager from hass.data
  - Remove config from hass.data

### Code Changes in `__init__.py`

```python
# In async_setup():
from .websocket_api import async_register_websocket_commands
async_register_websocket_commands(hass)

# In async_setup_entry():
from .action_manager import ActionManager
from .config_store import ConfigStore

hass.data.setdefault(DOMAIN, {})

# Setup action manager
action_manager = ActionManager(hass)
await action_manager.async_setup()
hass.data[DOMAIN]["action_manager"] = action_manager

# Setup config store
config_store = ConfigStore(hass)
await config_store.async_load()
hass.data[DOMAIN]["config"] = config_store.get_config()
hass.data[DOMAIN]["config_store"] = config_store

# In async_unload_entry():
hass.data[DOMAIN].pop("action_manager", None)
hass.data[DOMAIN].pop("config", None)
hass.data[DOMAIN].pop("config_store", None)
```

---

## Verification

```bash
# Run WebSocket API tests
pytest tests/test_websocket_api.py -v

# Start dev environment and test manually
./scripts/dev.sh

# In browser dev tools console:
# hass.connection.sendMessage({type: "abode_security/actions/list"})
```

## Notes

- Use `@websocket_api.websocket_command` decorator for each handler
- Use `@websocket_api.async_response` for async handlers
- Error codes: `not_found`, `validation_error`, `unknown_error`
- All WebSocket handlers should access `ActionManager` via `hass.data[DOMAIN]["action_manager"]`
