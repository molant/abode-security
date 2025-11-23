# Session Start Instructions

## Quick Context Check (Do This First!)

1. **Read DEVELOPMENT.md** to understand current status
   ```bash
   cat DEVELOPMENT.md | head -50
   ```

2. **Check git log** to see recent work
   ```bash
   git log --oneline -10
   ```

3. **Note the current phase** from DEVELOPMENT.md
   - Phase 1: Repository Setup (✅ COMPLETE)
   - Phase 2: Quality Improvements (next)
   - Phase 3: Advanced Features (future)

## Project Overview

**Project:** `abode-security` - Custom HACS Integration for Abode Security Systems

**Location:** `/Users/molant/src/home-assistant-things/abode-security/`

**Purpose:** Maintain an independent custom integration separate from Home Assistant core, with full control over features and release cycles.

## Key Architecture

- **Domain:** `abode_security`
- **Library Vendoring:** `lib/jaraco/abode/` (vendored jaraco.abode library)
- **Import Strategy:** Each module imports `from . import _vendor` to set up sys.path
- **Structure:** Standard HACS custom integration layout

## Critical Files to Know

| File | Purpose |
|------|---------|
| `DEVELOPMENT.md` | Session log, architecture decisions, progress tracking |
| `custom_components/abode_security/__init__.py` | Integration entry point |
| `custom_components/abode_security/manifest.json` | Integration metadata |
| `custom_components/abode_security/_vendor.py` | Library path injection |
| `.github/workflows/` | CI/CD automation |

## Current Status

**Phase:** Phase 1 - Repository Setup (✅ COMPLETE)

**Completed:**
- ✅ Directory structure created
- ✅ Files copied and updated from HA core
- ✅ Domain changed to `abode_security`
- ✅ Library vendoring complete
- ✅ Documentation created
- ✅ Git initialized with initial commits

**Next Phase Tasks:**
- [ ] Copy and adapt test files from HA core
- [ ] Run HACS validation
- [ ] Test installation in Home Assistant
- [ ] Implement runtime data migration
- [ ] Add PARALLEL_UPDATES constants
- [ ] Add entity categories

## Testing Environment

- **Real Abode System:** Available for testing
- **Sensors:** None currently connected (but alarm control works)
- **Can Test:** Manual alarm triggers, test mode, payloads

## Before Starting Work

1. Update DEVELOPMENT.md with your session goals
2. Create a git branch if making significant changes: `git checkout -b feature/description`
3. Commit regularly with clear messages

## Session Checklist

At the **start** of your session:
- [ ] Read this file and DEVELOPMENT.md
- [ ] Check git log to see recent commits
- [ ] Update DEVELOPMENT.md with "Currently Working On"

At the **end** of your session:
- [ ] Update DEVELOPMENT.md with progress
- [ ] Commit all changes with descriptive messages
- [ ] Note next steps clearly in DEVELOPMENT.md

## Useful Commands

```bash
# Check status
cd /Users/molant/src/home-assistant-things/abode-security
git status
git log --oneline -10

# Run validation
python -m script.hassfest validate custom_components/abode_security

# View structure
ls -la custom_components/abode_security/
ls -la lib/jaraco/abode/ | head -20

# Test imports
python3 -c "import sys; sys.path.insert(0, 'lib'); from jaraco.abode.client import Client; print('Import successful')"
```

## Contact Points

For questions about:
- **Project structure:** See DEVELOPMENT.md
- **Component code:** See relevant .py file in custom_components/abode_security/
- **Library issues:** See lib/jaraco/abode/ (vendored source)
- **Next tasks:** See "Next Session Checklist" in DEVELOPMENT.md
