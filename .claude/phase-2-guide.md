# Phase 2: Quality Improvements Guide

## Overview

Phase 2 focuses on implementing Home Assistant best practices and quality enhancements. This makes the integration more maintainable, aligned with HA standards, and prepares for future features.

## Phase 2 Tasks (In Order)

### 1. Copy and Adapt Test Files

**Files to copy from HA core:**
```
/Users/molant/src/home-assistant-things/home-assistant-core/tests/components/abode/
  ├── __init__.py
  ├── conftest.py
  ├── common.py
  ├── test_init.py
  ├── test_config_flow.py
  ├── test_alarm_control_panel.py
  ├── test_switch.py
  ├── test_binary_sensor.py
  ├── test_camera.py
  ├── test_cover.py
  ├── test_light.py
  ├── test_lock.py
  ├── test_sensor.py
  └── fixtures/
```

**Changes needed:**
- Update imports from `homeassistant.components.abode` to `custom_components.abode_security`
- Update domain from `"abode"` to `"abode_security"`
- Adjust fixture paths as needed
- Update test utility imports

**Location:** Create at `tests/` directory (already exists)

### 2. Run HACS Validation

```bash
cd /Users/molant/src/home-assistant-things/abode-security
python -m script.hassfest validate custom_components/abode_security
```

Expected output: No errors or warnings

### 3. Test in Home Assistant

Steps:
1. Create a test Home Assistant instance or use existing
2. Copy `custom_components/abode_security/` to test HA's custom_components
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Create Integration
5. Search for "Abode Security"
6. Complete setup flow with test credentials

### 4. Runtime Data Migration

**Goal:** Move from `hass.data[DOMAIN]` to `entry.runtime_data`

**Files to update:**
- `custom_components/abode_security/__init__.py` - Main integration data storage

**Changes in __init__.py:**

```python
# OLD (current):
hass.data[DOMAIN] = AbodeSystem(abode, polling)

# NEW:
entry.runtime_data = AbodeSystem(abode, polling)
```

Then update all references throughout:
```python
# OLD:
hass.data[DOMAIN].abode
hass.data[DOMAIN].polling

# NEW:
entry.runtime_data.abode
entry.runtime_data.polling
```

**Files affected:** All platform files that access the data
- `alarm_control_panel.py`
- `switch.py`
- `sensor.py`
- `binary_sensor.py`
- `camera.py`
- `cover.py`
- `light.py`
- `lock.py`
- `services.py`

### 5. Add PARALLEL_UPDATES Constants

**Goal:** Optimize entity updates for better performance

**Location:** Add to each platform file's `async_setup_entry()` function

```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode sensors based on config entry."""
    abode = hass.data[DOMAIN].abode

    # Add this:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][PARALLEL_UPDATES] = asyncio.Semaphore(1)

    # ... rest of setup
```

Or simpler approach - add at module level in each platform:
```python
PARALLEL_UPDATES = 1  # Update one entity at a time
```

### 6. Add Entity Categories

**Goal:** Better UI organization for helper entities

**Implementation:**

```python
# In alarm_control_panel.py
from homeassistant.helpers.entity import EntityCategory

class AbodeAlarm(AlarmControlPanelEntity):
    # Main panel - no category (primary entity)
    pass

# In switch.py
class AbodeTestModeSwitch(SwitchEntity):
    @property
    def entity_category(self) -> EntityCategory:
        """Return category of switch."""
        return EntityCategory.CONFIG  # For test mode switch
```

**Categories to use:**
- `EntityCategory.CONFIG` - Configuration helper (test mode switch)
- `EntityCategory.DIAGNOSTIC` - Diagnostic info
- Default (no category) - Primary control entities

### 7. Add Diagnostics Support

**Goal:** Help users debug issues by collecting system info

**Create file:** `custom_components/abode_security/diagnostics.py`

```python
"""Diagnostics support for Abode Security."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import AbodeSystem
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    abode_system: AbodeSystem = hass.data[DOMAIN]

    return {
        "polling": abode_system.polling,
        "device_count": len(abode_system.abode.devices),
        "unique_id": entry.unique_id,
    }
```

Then add to `manifest.json`:
```json
{
  "domain": "abode_security",
  ...
  "diagnostics": true
}
```

## Testing Phase 2 Changes

After each task:

1. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

2. **Check formatting:**
   ```bash
   python -m ruff format custom_components/abode_security
   python -m ruff check custom_components/abode_security
   ```

3. **Type checking:**
   ```bash
   python -m mypy custom_components/abode_security --ignore-missing-imports
   ```

4. **HACS validation:**
   ```bash
   python -m script.hassfest validate custom_components/abode_security
   ```

## Commit Strategy for Phase 2

After each completed subtask:

```bash
# Adapt tests
git add tests/
git commit -m "test: Add and adapt test files from HA core

- Copy test_*.py files from HA core
- Update imports to use abode_security domain
- Add fixtures for testing
- Update conftest.py for custom integration"

# Runtime data migration
git add custom_components/abode_security/
git commit -m "refactor: Migrate to ConfigEntry.runtime_data

- Replace hass.data[DOMAIN] with entry.runtime_data
- Update all platform files to use runtime_data
- Simplify data access pattern
- Better alignment with HA standards"

# PARALLEL_UPDATES
git add custom_components/abode_security/
git commit -m "perf: Add PARALLEL_UPDATES constants

- Add PARALLEL_UPDATES = 1 to platform files
- Improve concurrent entity update handling
- Reduce API load"

# Entity categories
git add custom_components/abode_security/
git commit -m "feat: Add entity categories

- Mark test mode switch as CONFIG category
- Organize helper entities
- Better UI presentation"

# Diagnostics
git add custom_components/abode_security/
git commit -m "feat: Add diagnostics support

- Create diagnostics.py module
- Enable config entry diagnostics
- Help users debug integration issues"
```

## Expected Completion Time

- Tests: 1-2 hours (copying and adapting)
- HACS validation: 15 minutes
- HA testing: 30 minutes
- Runtime data: 1-2 hours (refactoring all files)
- PARALLEL_UPDATES: 30 minutes
- Entity categories: 15 minutes
- Diagnostics: 30 minutes

**Total Phase 2 estimate:** 4-6 hours

## Phase 2 Success Criteria

✅ All tasks complete when:
- [ ] Tests copied and passing
- [ ] HACS validation passes
- [ ] Integration loads in Home Assistant
- [ ] Runtime data migration complete
- [ ] PARALLEL_UPDATES added to all platforms
- [ ] Entity categories applied
- [ ] Diagnostics module created
- [ ] All code formatted and type-checked
- [ ] DEVELOPMENT.md updated with Phase 2 completion notes
- [ ] New commits in git log documenting changes

## Next: Phase 3

After Phase 2 is complete, Phase 3 includes:
- Configuration options (disable dispatch, etc.)
- Advanced features from the feature wishlist
- Library async conversion planning
- Performance optimizations
