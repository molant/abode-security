# Phase 4.5.1: Import Path Refactoring

**Status**: ⏳ Planned (not yet started)
**Date**: 2024-12-18
**Goal**: Remove sys.path hack and use proper Python import patterns throughout the codebase

## Problem Statement

Currently, the test infrastructure uses a sys.path manipulation that creates inconsistent import paths:

### Current State (Anti-Pattern)

**Test setup** ([conftest.py:11-13](../../tests/conftest.py#L11-L13)):
```python
_CUSTOM_COMPONENTS_PATH = Path(__file__).resolve().parents[1] / "custom_components"
if (custom_components_path_str := str(_CUSTOM_COMPONENTS_PATH)) not in sys.path:
    sys.path.insert(0, custom_components_path_str)
```

This hack allows tests to import as:
```python
from abode_security.abode.exceptions import AuthenticationException
```

**Production code** was using relative imports:
```python
from .abode.exceptions import AuthenticationException
```

**The Problem**: Python treats these as **different classes**, causing:
- `isinstance()` checks to fail
- Exception catching to fail
- Mock patches to target wrong paths

### Temporary Workaround (Phase 4.5.2)

We fixed this by making production code use absolute imports matching test expectations:
```python
# In __init__.py
from abode_security.abode.exceptions import AuthenticationException
```

**This works but is an anti-pattern** because:
1. Production code should use relative imports within the same package
2. Makes code less portable (package name hardcoded)
3. Tighter coupling to package structure
4. The sys.path hack is still there, potentially causing other issues

## Recommended Solution: Option 3

Remove the sys.path manipulation and use consistent, proper import paths everywhere.

### Benefits

1. **Removes root cause**: No more sys.path manipulation
2. **Proper Python patterns**:
   - Production uses relative imports (`.abode.exceptions`)
   - Tests use proper absolute imports (`custom_components.abode_security.abode.exceptions`)
3. **No module identity issues**: Only one way to import
4. **More maintainable**: Clear, standard patterns
5. **No hidden surprises**: No sys.path magic

### Trade-offs

- **More verbose**: Test imports are longer
- **More changes needed**: All test files must be updated
- **One-time effort**: But results in cleaner long-term codebase

## Implementation Plan

### Step 1: Revert Production Code to Relative Imports

**Files to modify**:
- `custom_components/abode_security/__init__.py`
- `custom_components/abode_security/config_flow.py`

**Changes**:

```python
# BEFORE (current anti-pattern):
from abode_security.abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
)
from abode_security.abode.exceptions import Exception as AbodeException
from custom_components.abode_security.abode.client import Client as Abode

# AFTER (proper pattern):
from .abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
)
from .abode.exceptions import Exception as AbodeException
from .abode.client import Client as Abode
```

### Step 2: Remove sys.path Manipulation

**File**: `tests/conftest.py`

**Changes**:

```python
# REMOVE these lines (11-13):
_CUSTOM_COMPONENTS_PATH = Path(__file__).resolve().parents[1] / "custom_components"
if (custom_components_path_str := str(_CUSTOM_COMPONENTS_PATH)) not in sys.path:
    sys.path.insert(0, custom_components_path_str)
```

**Keep**: The comment on line 15-16 explaining where the vendored library is located

### Step 3: Update All Test Imports

**Pattern**: Find/replace across all test files

```python
# FIND:
from abode_security.abode.

# REPLACE WITH:
from custom_components.abode_security.abode.
```

**Files to update** (approximately):
- `tests/test_config_flow.py`
- `tests/test_init.py`
- `tests/test_alarm_control_panel.py`
- `tests/test_binary_sensor.py`
- `tests/test_camera.py`
- `tests/test_cover.py`
- `tests/test_light.py`
- `tests/test_lock.py`
- `tests/test_sensor.py`
- `tests/test_switch.py`
- `tests/test_cms_settings_switches.py`
- `tests/test_entity_lifecycle.py`
- `tests/test_integration_advanced_features.py`
- `tests/test_e2e_scenarios.py`
- Any other test files importing from `abode_security.abode.*`

### Step 4: Update Test Patches

All test patches are already using the correct paths from Phase 4.5.2:
```python
patch("custom_components.abode_security.abode.client.Client")
```

**Verify**: Check `tests/common.py` for any remaining short paths:
```python
# Current (needs update):
patch("abode_security.abode.event_controller.sio")

# Should be:
patch("custom_components.abode_security.abode.event_controller.sio")
```

### Step 5: Update conftest.py Fixtures

**File**: `tests/conftest.py`

**Verify** fixture imports use correct paths:
```python
# Line 19 - should be:
from custom_components.abode_security.abode.helpers import urls as url

# Line 271 - should be:
from custom_components.abode_security.abode.client import Client as Abode
```

## Files Affected

### Production Code (revert to relative imports)
- [ ] `custom_components/abode_security/__init__.py` - Lines 102-112
- [ ] `custom_components/abode_security/config_flow.py` - Exception imports

### Test Infrastructure
- [ ] `tests/conftest.py` - Remove sys.path hack (lines 11-13)
- [ ] `tests/conftest.py` - Update fixture imports (line 19, 271)
- [ ] `tests/common.py` - Update patch paths (line 36)

### Test Files (update imports)
Search for `from abode_security.abode.` and replace with `from custom_components.abode_security.abode.`:

- [ ] `tests/test_config_flow.py`
- [ ] `tests/test_init.py`
- [ ] `tests/test_alarm_control_panel.py`
- [ ] `tests/test_binary_sensor.py`
- [ ] `tests/test_camera.py`
- [ ] `tests/test_cover.py`
- [ ] `tests/test_light.py`
- [ ] `tests/test_lock.py`
- [ ] `tests/test_sensor.py`
- [ ] `tests/test_switch.py`
- [ ] `tests/test_cms_settings_switches.py`
- [ ] `tests/test_entity_lifecycle.py`
- [ ] `tests/test_integration_advanced_features.py`
- [ ] `tests/test_e2e_scenarios.py`
- [ ] Any other test files

## Testing Strategy

### Phase 1: Make Changes
1. Create a new branch: `git checkout -b refactor/import-paths`
2. Make all changes listed above
3. Run ruff format and check

### Phase 2: Verify Tests Still Pass
```bash
# Should still have 9 passing tests
python3 -m pytest tests/test_config_flow.py tests/test_init.py -v

# Expected: 9 passed
```

### Phase 3: Full Test Suite
```bash
# Run all tests to ensure nothing broke
python3 -m pytest tests/ -v

# Expected: Same results as before (9 passed, 213 skipped)
```

### Phase 4: Commit
```bash
git add -A
git commit -m "refactor: Use proper import paths (remove sys.path hack)

- Reverted production code to use relative imports
- Removed sys.path manipulation from conftest.py
- Updated all test imports to use proper absolute paths
- All 9 tests still passing

This removes the anti-pattern of absolute imports in production code
and the sys.path hack in test configuration."
```

## Success Criteria

- ✅ All 9 tests still passing
- ✅ Production code uses relative imports (`.abode.*`)
- ✅ Test code uses proper absolute imports (`custom_components.abode_security.abode.*`)
- ✅ No sys.path manipulation in conftest.py
- ✅ Ruff, mypy, pytest all pass
- ✅ No change in test coverage percentage

## Common Issues & Solutions

### Issue 1: Import Errors After Removing sys.path

**Symptom**: `ModuleNotFoundError: No module named 'abode_security'`

**Solution**: Update the import in the test file from:
```python
from abode_security.abode.exceptions import AuthenticationException
```
to:
```python
from custom_components.abode_security.abode.exceptions import AuthenticationException
```

### Issue 2: Mock Patches Not Working

**Symptom**: Tests fail because mocks aren't being applied

**Solution**: Ensure patch targets use full path:
```python
# Correct:
patch("custom_components.abode_security.abode.client.Client")

# Wrong:
patch("abode_security.abode.client.Client")
```

### Issue 3: Different Class Identity

**Symptom**: `isinstance()` or exception catching fails

**Solution**: This should be fixed by using consistent paths. If it still occurs, check:
1. Production code is using relative imports
2. Tests are using `custom_components.abode_security.abode.*`
3. No remaining sys.path manipulation

## Alternative: Keep Current Pattern (Not Recommended)

If you decide to keep the current pattern:

**Pros**:
- No changes needed
- Tests already working

**Cons**:
- Anti-pattern in production code
- sys.path hack remains (potential for bugs)
- Less maintainable
- Not standard Python practice

**Recommendation**: Do the refactoring. It's better to have clean, standard patterns.

## Context for Next Session

### What Was Done (Phase 4.5.2)
- Fixed tests by making production code use absolute imports
- This was a workaround to match test expectations
- Tests are passing but using anti-pattern

### Why This Refactoring
- User correctly identified absolute imports as anti-pattern
- Need to fix the root cause (sys.path hack)
- Should use proper Python patterns everywhere

### Next Steps
Follow the implementation plan above to:
1. Revert production to relative imports
2. Remove sys.path hack
3. Update all test imports to proper paths
4. Verify tests still pass
5. Commit changes

### Expected Outcome
- Cleaner, more maintainable codebase
- Standard Python import patterns
- All 9 tests still passing
- Ready to continue enabling more tests in Phase 4.5.3
