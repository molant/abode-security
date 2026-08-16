# Pending Features & Improvements

Deferred items, future enhancements, and "nice to have" improvements not implemented immediately.

## Open code-review findings

A parallel code review in April 2026 produced 9 GitHub issues spanning correctness, a11y, and refactors. Triage them before picking items below:

- [github.com/molant/abode-security/issues](https://github.com/molant/abode-security/issues)

The review also landed four direct fixes for production bugs (frontend WS contract, action-trigger restart false-fire + delay race, embedded library retry/shutdown races); those are done.

- [ ] `abode_security.trigger_automation` cannot report per-entity failure.
      `services.py:_trigger_automation` fans out over `async_dispatcher_send`
      and `switch.py:_trigger_wrapper` schedules the coroutine with
      `hass.add_job`, so the service call returns successfully even when every
      automation failed. `handle_abode_errors` re-raises specifically so
      failures stay visible to callers, and this is the one path where that
      contract isn't met — the entity now logs the failure against its own
      entity_id, which is the most a fire-and-forget path can do. Making the
      service await the entities (or collect results) would close the gap.

## Frontend Panel Enhancements

**Source**: Phase 5 & 6 of better-development

The frontend panel (`frontend/src/abode-panel.ts`) currently implements Actions (CRUD + test) and Modes tabs. Possible further additions:

- [ ] Display alarm panel status (armed/disarmed/home)
- [ ] Show device list with current states
- [ ] Arm/disarm controls
- [ ] Sensor state display with real-time updates
- [ ] CMS settings configuration UI
- [ ] Event timeline viewer
- [ ] Automation management

**E2E tests to add when panel is expanded:**

- [ ] Dashboard loads with sensor data
- [ ] Alarm mode display is correct
- [ ] Arm/disarm interactions work
- [ ] Sensor state changes reflect in UI

## Frontend Build Improvements

**Source**: Phase 5 of better-development

- [ ] Cache busting with timestamped filenames (deferred for simplicity)
  - Currently using fixed filename `abode-security-panel.js`
  - Would require updating panel registration to use dynamic filename
  - Could use a manifest file or HA's resource versioning

- [ ] **Enable `@typescript-eslint/no-floating-promises`** (deferred from PR #30)
  - Would catch unhandled promise rejections in async event handlers and
    fire-and-forget calls. The codebase has ~10 intentional patterns
    (`@click=${this._handleSave}`, `connectedCallback() { this._loadData(); }`)
    that would each need a `void` prefix or other annotation.
  - Requires `tseslint.configs.recommendedTypeChecked` (or scoped a la carte)
    plus `parserOptions.project: true` — slows lint runs.
  - PR11 deferred this to keep the baseline stack lean.

## Test Coverage

**Source**: Phase 4.5 of better-development

~120 tests are gated behind the `enabled_tests` allowlist in `tests/conftest.py`. Categories:

- [ ] **Advanced features tests** (~29 tests) - SmartPolling, EventFilter, BatchOperations — require full HA environment or more complex mocking
- [ ] **Async verification tests** (~27 tests) - Static analysis of async patterns — could be converted to simple unit tests
- [ ] **Entity lifecycle tests** (~9 tests) - Event subscription, error handling — need real entity instances
- [ ] **Exception tests** (~12 tests) - Exception class behavior — should be simple to enable
- [ ] **E2E scenario tests** (~10 tests) - Full workflow testing — could use mock server approach
- [ ] **Integration advanced features tests** (~18 tests) — require options flow and complex setup

## CI/CD Improvements

**Source**: Phase 7 of better-development

- [ ] Enable E2E tests in CI (currently disabled with `if: false`)
  - Remove `if: false` from `.github/workflows/e2e-tests.yaml`
  - Consider running on PR to main only (resource intensive)
- [ ] Add bundle size tracking/alerting
- [ ] Add test coverage reporting to PR comments

## Documentation

- [ ] Add API documentation for frontend components
- [ ] Document mock server endpoints more thoroughly

---

## How to Use This Document

1. **Adding items**: When deferring work, add it here with source reference
2. **Picking up items**: Check this list when looking for improvements to make
3. **Completing items**: Mark checkbox and add completion date, or remove if done as part of another feature
4. **Organizing**: Group related items under headings
5. **Correctness findings / bugs**: file on GitHub issues, not here

## Priority Guide

When picking up deferred items, consider:

- **Highest value**: Open GitHub issues (correctness, a11y)
- **High value**: Frontend panel enhancements (most user-visible)
- **Medium value**: Test coverage improvements (code quality)
- **Lower priority**: Build improvements, CI enhancements
