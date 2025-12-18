# Test Audit - Disabled Tests

**Last Updated**: 2024-12-17

## Summary
- **Total tests**: 222
- **Currently passing**: 86
- **Currently skipped**: 136
- **Skip reason**: "Requires full Home Assistant integration setup"

## Tests by Category

### ✅ Currently Passing (86 tests)
- `test_advanced_features.py` - All 29 tests passing (polling, event filters, batch operations)
- `test_async_await_verification.py` - All 24 tests passing (async patterns, service handlers)
- `test_async_static_analysis.py` - All 19 tests passing (static analysis, documentation)
- `test_exceptions.py` - All 10 tests passing (exception handling)
- `test_entity_lifecycle.py` - 2 tests passing (error handling for missing methods)

### 🔴 Alarm Control Panel Tests (6 tests - SKIPPED)
**File**: `tests/test_alarm_control_panel.py`

- `test_entity_registry` - SKIP: Requires full Home Assistant integration setup
- `test_attributes` - SKIP: Requires full Home Assistant integration setup
- `test_set_alarm_away` - SKIP: Requires full Home Assistant integration setup
- `test_set_alarm_home` - SKIP: Requires full Home Assistant integration setup
- `test_set_alarm_standby` - SKIP: Requires full Home Assistant integration setup
- `test_state_unknown` - SKIP: Requires full Home Assistant integration setup

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 Binary Sensor Tests (2 tests - SKIPPED)
**File**: `tests/test_binary_sensor.py`

- `test_entity_registry` - SKIP: Requires full Home Assistant integration setup
- `test_attributes` - SKIP: Requires full Home Assistant integration setup

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 Camera Tests (5 tests - SKIPPED)
**File**: `tests/test_camera.py`

- `test_entity_registry` - SKIP: Requires full Home Assistant integration setup
- `test_attributes` - SKIP: Requires full Home Assistant integration setup
- `test_capture_image` - SKIP: Requires full Home Assistant integration setup
- `test_camera_on` - SKIP: Requires full Home Assistant integration setup
- `test_camera_off` - SKIP: Requires full Home Assistant integration setup

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 CMS Settings Switch Tests (35 tests - SKIPPED)
**File**: `tests/test_cms_settings_switches.py`

**Monitoring Active** (7 tests):
- `test_monitoring_active_entity_registry`
- `test_monitoring_active_attributes`
- `test_monitoring_active_initial_status_on`
- `test_monitoring_active_initial_status_off`
- `test_monitoring_active_turn_on`
- `test_monitoring_active_turn_off`
- `test_monitoring_active_error_handling`

**Send Media** (7 tests):
- `test_send_media_entity_registry`
- `test_send_media_attributes`
- `test_send_media_initial_status_on`
- `test_send_media_initial_status_off`
- `test_send_media_turn_on`
- `test_send_media_turn_off`
- `test_send_media_error_handling`

**Dispatch Without Verification** (7 tests):
- `test_dispatch_without_verification_entity_registry`
- `test_dispatch_without_verification_attributes`
- `test_dispatch_without_verification_initial_status_on`
- `test_dispatch_without_verification_initial_status_off`
- `test_dispatch_without_verification_turn_on`
- `test_dispatch_without_verification_turn_off`
- `test_dispatch_without_verification_error_handling`

**Dispatch Police** (7 tests):
- `test_dispatch_police_entity_registry`
- `test_dispatch_police_attributes`
- `test_dispatch_police_initial_status_on`
- `test_dispatch_police_initial_status_off`
- `test_dispatch_police_turn_on`
- `test_dispatch_police_turn_off`
- `test_dispatch_police_error_handling`

**Dispatch Fire** (7 tests):
- Similar pattern...

**Dispatch Medical** (7 tests):
- Similar pattern...

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 Config Flow Tests (4 tests - SKIPPED)
**File**: `tests/test_config_flow.py`

- `test_one_config_allowed` - SKIP: Requires full Home Assistant integration setup
- `test_user_flow` - SKIP: Requires full Home Assistant integration setup
- `test_step_mfa` - SKIP: Requires full Home Assistant integration setup
- `test_step_reauth` - SKIP: Requires full Home Assistant integration setup

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 Cover Tests (4 tests - SKIPPED)
**File**: `tests/test_cover.py`

- `test_entity_registry`
- `test_attributes`
- `test_open`
- `test_close`

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 E2E Scenarios Tests (10 tests - SKIPPED)
**File**: `tests/test_e2e_scenarios.py`

**Full Setup Workflow** (4 tests):
- `test_user_adds_integration_and_configures_options`
- `test_integration_recovers_from_temporary_failure`
- `test_smart_polling_optimization_workflow`
- `test_event_filter_reduces_unnecessary_updates`

**Batch Operations Workflow** (2 tests):
- `test_batch_arm_disarm_multiple_devices`
- `test_batch_operations_with_partial_failures`

**Configuration Presets** (2 tests):
- `test_user_selects_aggressive_preset`
- `test_user_switches_between_presets`

**Error Recovery Scenarios** (2 tests):
- `test_graceful_recovery_from_network_error`
- `test_invalid_config_handling`

**Can enable with**: Mock server + full integration tests

---

### 🔴 Entity Lifecycle Tests (6 tests - SKIPPED)
**File**: `tests/test_entity_lifecycle.py`

- `test_manual_alarm_switch_subscribes_to_events`
- `test_manual_alarm_switch_unsubscribes_on_removal`
- `test_manual_alarm_switch_handles_missing_remove_callback`
- `test_alarm_control_panel_error_handling`
- `test_test_mode_switch_polling_disabled_initially`
- `test_event_callback_helpers_handle_exceptions`
- `test_service_handler_factory_error_handling`

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 Init Tests (5 tests - SKIPPED)
**File**: `tests/test_init.py`

- `test_change_settings`
- `test_add_unique_id`
- `test_unload_entry`
- `test_invalid_credentials`
- `test_raise_config_entry_not_ready_when_offline`

**Can enable with**: Mock server + HA test fixtures

---

### 🔴 Integration Advanced Features Tests (8 tests - SKIPPED)
**File**: `tests/test_integration_advanced_features.py`

**Smart Polling Integration** (4 tests):
- `test_smart_polling_initialized_with_presets`
- `test_smart_polling_tracks_update_statistics`
- `test_smart_polling_adapts_to_errors`
- `test_smart_polling_improves_with_good_performance`

**Event Filtering Integration** (4 tests):
- `test_event_filter_initialized_from_config`
- `test_event_filter_allows_all_by_default`
- `test_event_filter_filters_specified_events`
- `test_event_filter_tracks_statistics`

**Can enable with**: Mock server + full integration tests

---

### 🔴 Remaining Platform Tests (SKIPPED)
**Files**: `test_light.py`, `test_lock.py`, `test_sensor.py`, `test_services.py`, `test_switch.py`

Approximately 50+ tests skipped across these files.

**Can enable with**: Mock server + HA test fixtures

---

## Enablement Plan

### Phase 1: Infrastructure (Prerequisites)
- [x] Add mock server fixtures to conftest.py
- [x] Create integration test directory
- [x] Update pytest configuration with markers
- [x] Create example integration test

### Phase 2: Config Flow & Auth (Simplest - 4 tests)
- [ ] `test_config_flow.py` - 4 tests
  - Basic authentication flow
  - MFA handling
  - Reauth flow

### Phase 3: Alarm Control Panel (6 tests)
- [ ] `test_alarm_control_panel.py` - 6 tests
  - Entity registry
  - Attributes
  - Mode changes (away, home, standby)

### Phase 4: Init & Core (5 tests)
- [ ] `test_init.py` - 5 tests
  - Settings changes
  - Entry lifecycle
  - Credentials validation

### Phase 5: Simple Sensors (6 tests)
- [ ] `test_binary_sensor.py` - 2 tests
- [ ] `test_cover.py` - 4 tests

### Phase 6: Camera (5 tests)
- [ ] `test_camera.py` - 5 tests

### Phase 7: CMS Settings Switches (35 tests)
- [ ] `test_cms_settings_switches.py` - 35 tests
  - Monitoring active (7)
  - Send media (7)
  - Dispatch settings (21)

### Phase 8: Entity Lifecycle (7 tests)
- [ ] `test_entity_lifecycle.py` - 7 tests

### Phase 9: Remaining Platforms (~50 tests)
- [ ] `test_light.py`
- [ ] `test_lock.py`
- [ ] `test_sensor.py`
- [ ] `test_switch.py`
- [ ] `test_services.py`

### Phase 10: Integration & E2E (18 tests)
- [ ] `test_integration_advanced_features.py` - 8 tests
- [ ] `test_e2e_scenarios.py` - 10 tests

## Statistics Tracking

**Updated**: 2024-12-17

| Category | Total | Enabled | Remaining |
|----------|-------|---------|-----------|
| Config Flow & Auth | 4 | 0 | 4 |
| Alarm Control Panel | 6 | 0 | 6 |
| Init & Core | 5 | 0 | 5 |
| Binary Sensor | 2 | 0 | 2 |
| Camera | 5 | 0 | 5 |
| Cover | 4 | 0 | 4 |
| CMS Switches | 35 | 0 | 35 |
| Entity Lifecycle | 7 | 0 | 7 |
| Integration Features | 8 | 0 | 8 |
| E2E Scenarios | 10 | 0 | 10 |
| Other Platforms | ~50 | 0 | ~50 |
| **TOTAL** | **136** | **0** | **136** |

## Notes

- All skipped tests use the `hass` fixture which triggers the skip in `conftest.py:26-35`
- Most tests are well-structured and should be straightforward to enable
- CMS settings switches have repetitive patterns - might benefit from parameterization
- E2E scenarios will need more complex setup with full mock server state management
- Current coverage: 35% (can improve significantly once tests are enabled)
