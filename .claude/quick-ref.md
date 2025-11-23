# Quick Reference Card

## Project Info
- **Name:** abode-security
- **Domain:** abode_security
- **Type:** Custom HACS Integration
- **Path:** `/Users/molant/src/home-assistant-things/abode-security/`

## Key Locations

```
abode-security/
├── custom_components/abode_security/     # Main integration code
│   ├── __init__.py                       # Integration entry point
│   ├── _vendor.py                        # Library path setup
│   ├── manifest.json                     # Integration metadata
│   ├── const.py                          # Constants (DOMAIN = "abode_security")
│   ├── config_flow.py                    # Setup flow
│   ├── services.py                       # Service handlers
│   ├── entity.py                         # Base entity class
│   ├── alarm_control_panel.py            # Alarm panel platform
│   ├── switch.py                         # Switches (manual alarms + test mode)
│   ├── [binary_sensor|camera|cover|light|lock|sensor].py
│   └── translations/en.json              # Translations
├── lib/jaraco/abode/                     # Vendored library
│   ├── client.py                         # Main Abode client
│   ├── devices/                          # Device definitions
│   └── helpers/                          # Utilities
├── tests/                                # Test files (Phase 2)
├── .github/workflows/                    # CI/CD
├── DEVELOPMENT.md                        # Session log
├── README.md                             # User documentation
├── .claude/                              # Claude session files
│   ├── session-start.md                  # This session's starting point
│   ├── phase-2-guide.md                  # Phase 2 detailed guide
│   └── quick-ref.md                      # This file
└── pyproject.toml                        # Project config
```

## Current Status

| Item | Status |
|------|--------|
| Phase 1 Setup | ✅ Complete |
| Directory Structure | ✅ Done |
| Files Copied | ✅ Done |
| Domain Updated | ✅ Done |
| Library Vendoring | ✅ Done |
| Git Initialized | ✅ Done |
| Phase 2 Ready | 🔄 In Progress |

## Quick Commands

```bash
# Navigate to project
cd /Users/molant/src/home-assistant-things/abode-security

# Check status
git status
git log --oneline -10

# Read session guides
cat .claude/session-start.md
cat .claude/phase-2-guide.md

# Read project log
cat DEVELOPMENT.md | head -100

# List component files
ls custom_components/abode_security/*.py

# Check imports work
python3 -c "import sys; sys.path.insert(0, 'lib'); from jaraco.abode.client import Client; print('✓ Imports work')"

# Validate HACS format
python -m script.hassfest validate custom_components/abode_security

# Run tests (Phase 2+)
pytest tests/ -v

# Format code
python -m ruff format custom_components/abode_security

# Check code
python -m ruff check custom_components/abode_security
```

## Integration Architecture

### Domain
```python
DOMAIN = "abode_security"  # in const.py
```

### Entry Point
```
custom_components/abode_security/__init__.py
├── async_setup() - Module setup
├── async_setup_entry() - Config entry setup
└── async_unload_entry() - Cleanup
```

### Platforms
All platforms follow this pattern:
```python
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up platform from config entry."""
    abode_system = hass.data[DOMAIN]  # Access shared Abode client
    # ... create entities
    async_add_entities(entities)
```

### Vendored Library Access
```python
# All files that use jaraco.abode must start with:
from . import _vendor  # noqa: F401

# Then import normally:
from jaraco.abode.client import Client as Abode
from jaraco.abode.devices.alarm import Alarm
```

## Services Available

| Service | Domain Call | Purpose |
|---------|-------------|---------|
| `trigger_alarm` | `abode_security.trigger_alarm` | Manually trigger alarm |
| `acknowledge_alarm` | `abode_security.acknowledge_alarm` | Acknowledge alarm event |
| `dismiss_alarm` | `abode_security.dismiss_alarm` | Dismiss alarm event |
| `enable_test_mode` | `abode_security.enable_test_mode` | Disable dispatch (30min) |
| `disable_test_mode` | `abode_security.disable_test_mode` | Re-enable dispatch |

## File Structure Notes

### Imports Order
```python
"""Module docstring."""

from __future__ import annotations

# Standard library
import sys
from pathlib import Path

# Vendor setup (MUST be first jaraco usage)
from . import _vendor  # noqa: F401

# Jaraco imports (now vendored)
from jaraco.abode.devices.alarm import Alarm

# Home Assistant
from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity

# Local
from .const import DOMAIN
from .entity import AbodeDevice
```

### Entity Pattern
```python
class AbodeDevice(entity_base_class):
    """Base class for Abode entities."""

    def __init__(self, abode_device: AbodeDev, abode_system: AbodeSystem):
        """Initialize."""
        self.abode_device = abode_device
        self.abode_system = abode_system

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.abode_device.device_id)},
            name=self.abode_device.name,
        )
```

## Testing Environment

- **Real Abode Hub:** Available
- **Sensors:** None connected (currently)
- **Can Test:** Alarm control, manual triggers, test mode, event payloads

## Common Development Tasks

### Add a New Service

1. Update `services.yaml` with service definition
2. Update `strings.json` with translations
3. Add handler function in `services.py`
4. Register in `async_setup_services()` in `services.py`
5. Add test in `tests/test_services.py` (Phase 2+)

### Modify an Entity

1. Find the file: `platform_name.py`
2. Update the entity class
3. Make sure `from . import _vendor` is imported
4. Test platform files to ensure they're updated

### Update the Vendor Library

1. Fetch new jaraco.abode source
2. Replace contents of `lib/jaraco/abode/`
3. Test that imports still work
4. Commit with detailed message noting library version

## Phase Progress

```
Phase 1: Repository Setup
┌─────────────────────────────┐
│ ✅ Complete               │
├─────────────────────────────┤
│ • Directory structure       │
│ • Files copied & updated    │
│ • Library vendored          │
│ • Documentation created     │
│ • Git initialized           │
└─────────────────────────────┘

Phase 2: Quality Improvements
┌─────────────────────────────┐
│ 🔄 In Progress             │
├─────────────────────────────┤
│ • Test files                │
│ • HACS validation           │
│ • Runtime data migration    │
│ • PARALLEL_UPDATES          │
│ • Entity categories         │
│ • Diagnostics               │
└─────────────────────────────┘

Phase 3: Advanced Features
┌─────────────────────────────┐
│ ⏳ Future                   │
├─────────────────────────────┤
│ • Configuration options     │
│ • Library async conversion  │
│ • Advanced features         │
└─────────────────────────────┘
```

## Remember

1. **Always check DEVELOPMENT.md** for current status before starting
2. **Read phase guide** for the phase you're working on
3. **Commit frequently** with clear, descriptive messages
4. **Update DEVELOPMENT.md** when your session ends
5. **Use git branch** for experimental changes
6. **Test in HA** before marking tasks complete
