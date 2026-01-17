# Pending Features & Improvements

This document tracks deferred items, future enhancements, and "nice to have" improvements that were identified during feature development but not implemented immediately.

## Frontend Panel Enhancements

**Source**: Phase 5 & 6 of better-development

The current frontend panel (`frontend/src/abode-panel.ts`) is a minimal implementation showing "Abode Configuration" text. The following functionality could be added:

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

## Test Coverage

**Source**: Phase 4.5 of better-development

125 tests are currently skipped. Categories:

- [ ] **Advanced features tests** (~29 tests) - SmartPolling, EventFilter, BatchOperations
  - Require full HA environment or more complex mocking
- [ ] **Async verification tests** (~27 tests) - Static analysis of async patterns
  - Could be converted to simple unit tests
- [ ] **Entity lifecycle tests** (~9 tests) - Event subscription, error handling
  - Need real entity instances
- [ ] **Exception tests** (~12 tests) - Exception class behavior
  - Should be simple to enable
- [ ] **E2E scenario tests** (~10 tests) - Full workflow testing
  - Could use mock server approach
- [ ] **Integration advanced features tests** (~18 tests)
  - Require options flow and complex setup

## CI/CD Improvements

**Source**: Phase 7 of better-development

- [ ] Enable E2E tests in CI (currently disabled with `if: false`)
  - Remove `if: false` from `.github/workflows/e2e-tests.yaml`
  - Consider running on PR to main only (resource intensive)
- [ ] Add bundle size tracking/alerting
- [ ] Add test coverage reporting to PR comments

## Documentation

- [ ] Add API documentation for frontend components
- [ ] Add architecture diagram
- [ ] Document mock server endpoints more thoroughly

---

## How to Use This Document

1. **Adding items**: When deferring work, add it here with source reference
2. **Picking up items**: Check this list when looking for improvements to make
3. **Completing items**: Mark checkbox and add completion date, or remove if done as part of another feature
4. **Organizing**: Group related items under headings

## Priority Guide

When picking up deferred items, consider:
- **High value**: Frontend panel enhancements (most user-visible)
- **Medium value**: Test coverage improvements (code quality)
- **Lower priority**: Build improvements, CI enhancements
