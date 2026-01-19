# Dashboard Configuration Feature - Implementation Guide

## Status

**IMPLEMENTED** - All phases complete.

## Implementation Phases

The implementation is split into 5 phases with detailed specs:

| Phase | File | Description | Status |
|-------|------|-------------|--------|
| 1 | [phase-1-action-model.md](phase-1-action-model.md) | AbodeAction dataclass and ActionStore | complete |
| 2 | [phase-2-action-manager.md](phase-2-action-manager.md) | ActionManager CRUD and validation | complete |
| 3 | [phase-3-websocket-api.md](phase-3-websocket-api.md) | WebSocket API endpoints | complete |
| 4 | [phase-4-action-trigger.md](phase-4-action-trigger.md) | Action trigger coordinator | complete |
| 5 | [phase-5-frontend.md](phase-5-frontend.md) | Frontend UI components | complete |

## Confirmed Requirements

- **Mode naming**: `standby`/`home`/`away` (matching Abode API)
- **Action targets**: Trigger alarm switches + fire HA events (for user automations)
- **Auto-start**: Coordinator starts automatically on integration setup
- **Debouncing**: Global setting (not per-action)
- **Sensor scope**: All HA binary sensors (not just Abode)
- **Delay**: Optional per-action delay (0-60 seconds)
- **Test button**: Yes, for manual testing of actions
- **UX**: Basic loading/error handling (spinner, toast notifications)

## Overview

This feature implements a custom Home Assistant panel for configuring Abode alarm actions. Actions are custom automation rules that trigger alarm switches when specific sensors activate while in specific alarm modes (standby, home, away).

## Architecture

### Data Flow

```
User (Frontend Panel)
    ↓
WebSocket API
    ↓
ActionManager (CRUD + Storage)
    ↓
Home Assistant Store (Persistent)

ActionTriggerCoordinator (Event Listener)
    ↓ (listens to)
Binary Sensor State Changes
    ↓
Queries ActionManager for matching actions
    ↓
Triggers Alarm Switches via HA Services
    ↓
Fires HA Events for user automations
```

## Components

### 1. Action Management (`action_manager.py`)

#### AbodeAction Model
```python
@dataclass
class AbodeAction:
    id: str                           # UUID
    name: str                         # User-friendly name
    modes: list[str]                  # ["standby", "home", "away"]
    sensor_entity_ids: list[str]      # Any HA binary sensors
    alarm_entity_ids: list[str]       # Abode alarm switches to trigger
    enabled: bool = True
    delay_seconds: int = 0            # 0-60, delay before triggering
    last_triggered: datetime | None   # When action last triggered
    trigger_count: int = 0            # How many times triggered
```

#### ActionStore
- Uses Home Assistant's `Store` API for persistence
- Stores data in `.storage/abode_security_actions.json`
- Automatically loads on startup
- Serializes/deserializes datetime fields to ISO format

#### ActionManager
- **CRUD Methods:**
  - `async_create()` - Create new action with validation
  - `async_get()` - Retrieve action by ID
  - `async_get_all()` - Get all actions
  - `async_update()` - Update action with validation
  - `async_delete()` - Delete action

- **Helper Methods:**
  - `async_get_by_mode()` - Get actions for specific mode
  - `async_get_enabled()` - Get only enabled actions
  - `async_toggle()` - Enable/disable action
  - `async_record_trigger()` - Update trigger statistics

- **Validation Rules:**
  - Action name cannot be empty
  - At least one mode must be selected (standby, home, away)
  - At least one sensor must be selected
  - At least one alarm must be selected
  - Delay must be 0-60 seconds

### 2. Action Triggering (`action_trigger.py`)

#### ActionTriggerCoordinator
Listens to Home Assistant state changes and triggers matching actions.

**Workflow:**
1. Subscribes to `state_changed` events for all binary sensors
2. When a sensor state changes to "on":
   - Gets current alarm mode from `alarm_control_panel.abode_alarm`
   - Queries ActionManager for enabled actions matching:
     - Current mode is in action's modes list
     - Sensor entity ID is in action's sensors list
   - For each matching action:
     - Triggers all alarm switches via HA services
     - Records trigger statistics
     - Fires `abode_security.action_triggered` event

**Features:**
- Debouncing (configurable, default 1 second) prevents rapid re-triggers
- Only processes binary sensors that change to "on" state
- Gracefully handles missing alarm_control_panel
- Logs all triggers for debugging

**Event Structure:**
```python
{
    "action_id": str,
    "action_name": str,
    "triggered_by": str,        # sensor entity_id
    "mode": str,                # "standby", "home", "away"
    "alarms": list[str],        # alarm entity_ids triggered
    "timestamp": str,           # ISO format datetime
}
```

### 3. WebSocket API (`websocket_api.py`)

#### Commands

**List Actions**
```
Command: abode_security/actions/list
Response: { "actions": [...] }
```

**Get Action**
```
Command: abode_security/actions/get
Parameters: action_id
Response: { "id", "name", "modes", "sensor_entity_ids", "alarm_entity_ids", "enabled", "last_triggered", "trigger_count" }
```

**Create Action**
```
Command: abode_security/actions/create
Parameters: name, modes, sensor_entity_ids, alarm_entity_ids
Response: Created action object
Validation Errors: "validation_error" with error message
```

**Update Action**
```
Command: abode_security/actions/update
Parameters: action_id, name, modes, sensor_entity_ids, alarm_entity_ids
Response: Updated action object
```

**Delete Action**
```
Command: abode_security/actions/delete
Parameters: action_id
Response: { "success": true }
```

**Toggle Action**
```
Command: abode_security/actions/toggle
Parameters: action_id
Response: Updated action object with toggled enabled state
```

**Test Action**
```
Command: abode_security/actions/test
Parameters: action_id
Response: { "success": true, "alarms_triggered": [...] }
```

**List Modes**
```
Command: abode_security/modes/list
Response: [
    { "id": "standby", "name": "Standby", "icon": "mdi:lock-open", "action_count": 1, "active": false },
    { "id": "home", "name": "Home", "icon": "mdi:home", "action_count": 3, "active": true },
    { "id": "away", "name": "Away", "icon": "mdi:shield-check", "action_count": 2, "active": false }
]
```

**Get Sensors**
```
Command: abode_security/entities/sensors
Response: {
    "sensors": {
        "door": [...],
        "window": [...],
        "motion": [...],
        "moisture": [...],
        "smoke": [...],
        "connectivity": [...],
        "other": [...]
    }
}
```

**Get Alarms**
```
Command: abode_security/entities/alarms
Response: {
    "alarms": [
        { "entity_id": "switch.abode_panic_alarm", "name": "Panic Alarm", "type": "panic" },
        ...
    ]
}
```

**Get Config**
```
Command: abode_security/config/get
Response: { "debounce_seconds": 1.0 }
```

**Set Config**
```
Command: abode_security/config/set
Parameters: debounce_seconds (0.1 to 10.0)
Response: { "debounce_seconds": 2.0 }
```

## Integration Points

### Models (`models.py`)
- `AbodeSystem` dataclass extended with `action_manager` field
- Initialized in `async_setup_entry()`

### Setup (`__init__.py`)
- `ActionManager` imported and initialized
- WebSocket handlers registered in `async_setup()`
- Actions loaded on integration startup
- Event coordinator could be added to `async_setup_entry()` for production

### Storage
- Location: `.storage/abode_security_actions.json`
- Format: JSON with version field
- Automatically handled by Home Assistant Store API

## Testing

### Unit Tests

**test_action_manager.py** (~30 tests)
- AbodeAction serialization/deserialization
- Validation rules (empty name, missing modes, missing sensors, missing alarms)
- CRUD operations (create, get, update, delete)
- Mode filtering (get by mode)
- Action state (enabled/disabled, toggle)
- Persistence (cross-manager loading)

**test_action_trigger.py** (~15 tests)
- Coordinator initialization
- Mode conversion from alarm state
- Connect/disconnect lifecycle
- Trigger matching (sensor + mode)
- Multiple action triggering
- Event firing
- Debouncing
- State change filtering (non-on states, non-binary-sensors)
- Missing alarm_control_panel handling
- Delayed trigger cancellation on action delete/disable

**test_websocket_api.py** (~20 tests)
- All CRUD endpoints
- Authorization (admin required for mutations)
- Validation error responses
- Entity query endpoints
- Config get/set
- Concurrent operations (race conditions)

### Integration Tests

**test_actions_integration.py** (`@pytest.mark.integration`)
- Full flow with mock Abode server
- WebSocket API through actual HA WebSocket client
- Coordinator trigger flow with real state changes

### E2E Tests

**tests/e2e/test_actions_panel.spec.ts**
- Panel loads in sidebar
- Tab navigation works
- Create/edit/delete actions through UI
- Toggle enable/disable
- Test action with confirmation
- Form validation errors display
- Mobile viewport responsive layout

### Frontend Unit Tests

**frontend/src/__tests__/** (using `@open-wc/testing`)
- Component rendering
- Event dispatching
- Form validation logic

Run tests:
```bash
# Unit tests
pytest tests/test_action_manager.py tests/test_action_trigger.py tests/test_websocket_api.py -v

# Integration tests
pytest -m integration -v

# E2E tests
npm run test:e2e

# Frontend tests
cd frontend && npm test
```

## Usage Examples

### Create an Action via WebSocket
```javascript
// Listen for responses
connection.addEventListener('result', (event) => {
    console.log('Action created:', event.detail.result);
});

// Send create command
connection.send(JSON.stringify({
    type: 'abode_security/actions/create',
    name: 'Motion Alert Away',
    modes: ['away'],
    sensor_entity_ids: ['binary_sensor.backyard_motion'],
    alarm_entity_ids: ['switch.panic_alarm'],
    id: 1
}));
```

### Listen for Action Triggered Events
```python
# In Home Assistant automation
- alias: 'Log action trigger'
  trigger:
    platform: event
    event_type: abode_security.action_triggered
  action:
    service: logger.log
    data:
      message: "Action {{ trigger.event.data.action_name }} triggered by {{ trigger.event.data.triggered_by }}"
```

### Get All Sensors
```javascript
connection.send(JSON.stringify({
    type: 'abode_security/entities/sensors',
    id: 2
}));
```

## Frontend Integration (Phase 5)

The WebSocket API is ready for a custom Lit-based panel with:
1. **Modes Tab** - Show modes with action counts
2. **Actions Tab** - List/manage actions with CRUD
3. **Action Editor** - Form to create/edit actions with sensor/alarm selection

## Security

### Authorization

All mutation endpoints (create, update, delete, test) require **admin** privileges:
- Use `@websocket_api.require_admin` decorator
- Read-only endpoints (list, get) available to all authenticated users

### Input Validation

- **Action names**: Max 100 characters, HTML-escaped in frontend
- **Entity IDs**: Validated format, warn if entity doesn't exist (don't block)
- **Modes**: Only accept `["standby", "home", "away"]`

### Audit Logging

Log all mutations at INFO level:
```python
_LOGGER.info("Action %s created by user %s", action.id, connection.user.id)
```

### Test Action Safety

The "Test Action" feature triggers real alarms. Implementation must:
- Require confirmation in frontend before executing
- Log test triggers separately for audit purposes

## Known Limitations

1. **No AND/OR Logic** - Actions trigger if ANY sensor activates (v1 only)
2. **No Time-based Triggering** - Actions are mode-based only
3. **No Action Scheduling** - Actions trigger immediately (delay is pre-trigger only)
4. **Single Integration** - Assumes single Abode account per Home Assistant instance

## Future Enhancements

1. **Advanced Logic**
   - AND/OR sensor combinations
   - Time-based conditions
   - Condition-based enabling/disabling

2. **Automation Integration**
   - Custom action conditions
   - Action scheduling
   - Action priorities/ordering

3. **Monitoring**
   - Action history/log
   - Trigger statistics dashboard
   - Performance monitoring

4. **UI Improvements**
   - Action templates/presets
   - Bulk operations
   - Import/export

## Debugging

### Enable Debug Logging
```yaml
logger:
  logs:
    custom_components.abode_security.action_manager: debug
    custom_components.abode_security.action_trigger: debug
    custom_components.abode_security.websocket_api: debug
```

### Check Stored Actions
```bash
# From Home Assistant config directory
cat .storage/abode_security_actions.json | python3 -m json.tool
```

### WebSocket Testing
Use Home Assistant's WebSocket API debugger in Developer Tools

## Files Structure

```
custom_components/abode_security/
├── action_manager.py           # Action CRUD + storage (NEW - Phase 1-2)
├── action_trigger.py           # Event-driven triggering (NEW - Phase 4)
├── websocket_api.py            # Frontend API endpoints (NEW - Phase 3)
├── __init__.py                 # (modified) Setup integration
└── www/
    └── abode-security-panel.js # Built frontend (Phase 5)

frontend/
├── src/
│   ├── abode-panel.ts          # Main panel (expand existing)
│   ├── modes-tab.ts            # Modes display (NEW)
│   ├── actions-tab.ts          # Actions list (NEW)
│   ├── action-editor.ts        # Action form (NEW)
│   └── types.ts                # TypeScript types (expand existing)
└── package.json

tests/
├── test_action_manager.py      # ~30 unit tests (NEW)
├── test_action_trigger.py      # ~15 unit tests (NEW)
└── test_websocket_api.py       # ~15 unit tests (NEW)

features/dashboard-configuration/
├── dashboard-configuration.md  # Original feature requirements (archived)
├── README.md                   # This file (design spec)
├── phase-1-action-model.md     # Phase 1 spec
├── phase-2-action-manager.md   # Phase 2 spec
├── phase-3-websocket-api.md    # Phase 3 spec
├── phase-4-action-trigger.md   # Phase 4 spec
└── phase-5-frontend.md         # Phase 5 spec
```

## Getting Started

To implement this feature, start with Phase 1:

```bash
/spec-implement features/dashboard-configuration/phase-1-action-model.md
```

After completing each phase, proceed to the next:

```bash
/spec-implement features/dashboard-configuration/phase-2-action-manager.md
# ... and so on
```

## Contributing

When working on this feature:
- Follow the existing code style (TDD, type hints, docstrings)
- Write tests for new functionality
- Update phase status in this file when complete
- Use the `.githooks/pre-commit` hook before committing
