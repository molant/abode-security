---
status: pending
phase: 1
feature: abode-fork-modernization
title: Fork hygiene and dynamic-discovery audit
---

# Phase 1: Fork Hygiene and Dynamic-Discovery Audit

Add the fork-lineage record, delete the one provably-dead artifact in the vendored tree, and instrument the dynamic-discovery path so Phase 4 has data to decide on further deletes. Zero runtime behavior change.

## Context

The `custom_components/abode_security/abode/` directory is a vendored fork of `jaraco.abode`, modernized in place since 2025-12-01. There is no `UPSTREAM.md`, no policy note, and no mechanism for telling future contributors what's drift vs. intentional divergence. Meanwhile, `devices/base.py` calls `pkg.import_all()` from `Device.new(...)` on every device-construction path; the import work is cached after the first call, but the dynamic registration surface is exercised there. A device module being unimported by the outer integration is therefore **not** evidence that it's dead.

Phase 1 establishes the paper trail and the audit data without changing behavior. It must land cleanly and reviewably on its own.

Read [./README.md](./README.md) for overall feature context — especially the "Concepts" section on the divergence policy and dynamic-discovery surface.

## Structure

```
custom_components/abode_security/abode/
  UPSTREAM.md                  # new: fork lineage + divergence policy
  artifacts/
    test-mode-requests         # delete: 18.8K of captured-curl scratch with no code reference
  devices/
    base.py                    # update: add audit-only log line near pkg.import_all() call
features/abode-fork-modernization/
  phase-1-fork-hygiene.md      # this file (status: pending → done)
```

## Implementation Checklist

> Update these checkboxes as you complete each task!

### Baseline test verification (before starting implementation)

- [ ] Run `./scripts/check.sh` — lint + typecheck + unit tests must be clean.
- [ ] Run `uv run pytest -m integration` against `./scripts/dev.sh` — all 104 integration-collected items pass.
- [ ] Note the baseline test count (`uv run pytest --collect-only -q | tail -1`) and record it in the PR description. Any change in this number after Phase 1 must be explainable.

### Sub-Phase 1A: UPSTREAM.md

Create `custom_components/abode_security/abode/UPSTREAM.md` recording the lineage and policy. This is the file that turns "we have a vendored fork" from tribal knowledge into a documented decision.

The file must include, at minimum:

- **Upstream**: `https://github.com/jaraco/jaraco.abode`
- **Fork commit**: `aee5d16386c8747191d52fd2197c0e5dc40d4522` (this repo's first commit that added the `abode/` tree)
- **Fork date**: `2025-12-01`
- **Local commits modifying the fork**: count via `git log --oneline -- custom_components/abode_security/abode/ | wc -l` at write time; quote the actual number rather than reusing the spec-review baseline.
- **Intentional deletions vs. upstream**: `cli.py`, `__main__.py`, `keyring`-based credential persistence. These were removed during async modernization.
- **Intentional rewrites**: synchronous HTTP and threading replaced with `aiohttp` and (after Phase 3) `asyncio`-native I/O.
- **Sync policy**: "Hard divergence. No scheduled upstream sync, no quarterly diff review. If a CVE is filed against `jaraco.abode` and our fork is affected, do a targeted one-time backport. Do not enable Dependabot or other automation against this directory."
- **Tasks**:
  - [ ] Create the file with the structure above.
  - [ ] Cross-reference [#62](https://github.com/molant/abode-security/issues/62) and this spec from the top of the file.
  - [ ] Run `./scripts/check.sh` and confirm it stays clean. (UPSTREAM.md is markdown — neither pyright nor mypy touches it; the check is that lint/formatters don't object to anything in the markdown.)

### Sub-Phase 1B: Delete `abode/artifacts/test-mode-requests`

The file is 18.8K of captured `curl` commands from the Abode web UI's developer-tools panel. No Python module references the `artifacts/` directory; the file is not loaded at runtime, not parsed by tests, not consumed by anything in the repo.

- [ ] Verify zero references: `grep -rn "artifacts/\|test-mode-requests" custom_components/ tests/ scripts/ docs/ --include="*.py" --include="*.json" --include="*.yaml" --include="*.yml" --include="*.toml" --include="*.md"` — expect no hits outside this spec file.
- [ ] `git rm custom_components/abode_security/abode/artifacts/test-mode-requests`.
- [ ] If `custom_components/abode_security/abode/artifacts/` is now empty, remove the directory too.
- [ ] Re-run baseline tests; nothing should change.

### Sub-Phase 1C: Instrument `pkg.import_all()` for the dynamic-discovery audit

`devices/base.py` defines `Device.new(cls, state, client)` (a classmethod). That method calls `pkg.import_all()` **on every invocation** — once per device-instance construction during a test run, which can be hundreds of times. `pkg.import_all()` itself is idempotent (it relies on `importlib.import_module`, and after the first call every module is cached in `sys.modules`), so the *registration* happens once; but a literal `log.info(...)` placed "immediately after `pkg.import_all()`" would fire on every `Device.new` call.

The audit must therefore be **gated on a "logged once" sentinel** so it emits exactly one line per process. After the first emission, `iter_subclasses(Device)` reveals every registered concrete class — that's the snapshot Phase 4 needs.

The audit is **log-only** in this phase. No deletes happen here. The log line goes through the standard `logging` module so it's captured by the existing integration-test log machinery without any new plumbing.

- [ ] In `devices/base.py`, add a module-level sentinel and a helper function. Module-level (not class-level) keeps the sentinel alive across `Device` subclass changes during tests:
  ```python
  _AUDIT_LOGGED = False

  def _log_registered_classes_once() -> None:
      global _AUDIT_LOGGED
      if _AUDIT_LOGGED:
          return
      _AUDIT_LOGGED = True
      registered = sorted(cls.__module__ for cls in iter_subclasses(Device))
      log.info(
          "abode_security.audit.registered_device_classes=%s",
          ",".join(registered),
      )
  ```
- [ ] Call `_log_registered_classes_once()` from inside `Device.new`, immediately after `pkg.import_all()`. The sentinel makes this a one-shot per process even though `Device.new` runs per device.
  - Log key (Phase 4 greps for this exact string): `abode_security.audit.registered_device_classes`.
  - Format: `abode_security.audit.registered_device_classes=<comma-joined-sorted-list>`.
  - Use the file's existing `log` logger; do not introduce a new logger.
- [ ] Add a unit test in `tests/test_pkg_import_audit.py` (new file). The test must:
  - Reset the sentinel before the test (`base._AUDIT_LOGGED = False`) so the log fires.
  - Assert (via `caplog`) that calling `_log_registered_classes_once()` emits exactly one log record whose message contains `abode_security.audit.registered_device_classes=`.
  - Assert that `iter_subclasses(Device)` returns at least the **9 concrete device modules** known to be live today: `alarm`, `binary_sensor`, `camera`, `cover`, `light`, `lock`, `sensor`, `switch`, `valve`. `base.py` defines `Device` itself and will NOT appear in `iter_subclasses(Device)` — only concrete subclasses do.
  - Assert that calling the helper twice only emits one record (the sentinel is honored).
  - Use the existing test conventions in `tests/test_*.py` — `aioresponses` is not needed for this test.
  - Do NOT mark this test `@pytest.mark.integration`.
- [ ] Run `./scripts/check.sh` — must pass.
- [ ] Run `uv run pytest tests/test_pkg_import_audit.py -v` — must pass.

### Documentation (end of phase)

- [ ] `docs/ARCHITECTURE.md` — add a short note under the vendored-fork section pointing at `custom_components/abode_security/abode/UPSTREAM.md`. Do not edit the SocketIO section here — Phase 4 owns those edits.
- [ ] `CLAUDE.md` (root of this directory) — no change. The fork-policy detail lives in `UPSTREAM.md` to keep CLAUDE.md focused on day-to-day workflows.

### Build verification (required before marking phase complete)

- [ ] `./scripts/check.sh` — clean.
- [ ] `uv run pytest` — full unit suite green.
- [ ] `uv run pytest -m integration` (against `./scripts/dev.sh`) — all 104 integration items green.
- [ ] **Capture audit output**: grep the integration-test run's log for `abode_security.audit.registered_device_classes=` and paste the full registered-class list into a follow-up comment on the PR. Phase 4 will ingest this.
- [ ] Scan test/build output for new warnings or deprecation notices unrelated to this phase's edits. A zero exit code does not mean clean output.
- [ ] If `package-lock.json`, `pubspec.lock`, or other lockfiles changed, stage them. (Expected: none — Phase 1 touches no dependencies.)
- [ ] Mark this file's frontmatter `status: done` only after every box above is checked.

### Manual verification with MCP tools (if available)

Phase 1 has no end-user-visible change. Skip MCP verification — Phase 3 is the first place a user could observe a difference.

## Technical Details

### `UPSTREAM.md` template

Use this skeleton as the starting point; fill in real values at write time. Wikilinks (`[[...]]`) are not used in this project — use plain markdown links.

```markdown
# Vendored `jaraco.abode` Fork

Tracking: [#62](https://github.com/molant/abode-security/issues/62)
Spec: [features/abode-fork-modernization/README.md](../../../features/abode-fork-modernization/README.md)

## Lineage

| Field | Value |
|-------|-------|
| Upstream | https://github.com/jaraco/jaraco.abode |
| Fork commit (this repo) | `aee5d16386c8747191d52fd2197c0e5dc40d4522` |
| Fork date | 2025-12-01 |
| Local commits modifying this directory | <run `git log --oneline -- custom_components/abode_security/abode/ \| wc -l` and put the count here> |

## Intentional divergence

These changes are deliberate and must not be reverted by a sync:

- `cli.py`, `__main__.py` removed — no command-line interface in HA-integration context.
- `keyring`-based credential persistence removed — HA owns config storage.
- Synchronous HTTP (`requests`) replaced with `aiohttp.ClientSession`.
- (Phase 3, future) `lomond` WebSocket transport replaced with `aiohttp.ClientWebSocketResponse`; SocketIO daemon thread folded into the HA event loop.

## Sync policy

This fork is hard-diverged from upstream. We do **not** run a scheduled
upstream sync, a quarterly diff review, or any automation against this
directory.

**Exception**: if a CVE is filed against `jaraco.abode` and our fork is
affected, do a one-time targeted backport. Note it in this file under a
"Backport history" section. Otherwise, treat upstream as a reference, not
a source.

## Dynamic discovery surface

`devices/base.py` calls `pkg.import_all()` which walks the `devices/`
package and triggers concrete `Device` subclass registration via
`_ancestry.iter_subclasses`. **Removing a device module without first
checking the audit log will silently disable that device type.** Phase 1
of the fork-modernization spec adds a log line capturing the registered
class list; see that log before any module deletion.
```

### Audit log shape

Phase 4 will grep for `abode_security.audit.registered_device_classes=`. Keep the log key and format stable across implementations to avoid breaking Phase 4's ingestion step.

Expected output during an integration-test run, given today's state:

```
INFO custom_components.abode_security.abode.devices.base: abode_security.audit.registered_device_classes=custom_components.abode_security.abode.devices.alarm,custom_components.abode_security.abode.devices.binary_sensor,custom_components.abode_security.abode.devices.camera,custom_components.abode_security.abode.devices.cover,custom_components.abode_security.abode.devices.light,custom_components.abode_security.abode.devices.lock,custom_components.abode_security.abode.devices.sensor,custom_components.abode_security.abode.devices.switch,custom_components.abode_security.abode.devices.valve
```

Modules **not** appearing in that list are candidates for Phase 4 deletion. `base.py` and `status.py` are intentionally not concrete `Device` subclasses; they will not appear in the audit and are not delete candidates.

## Constraints

- **Zero runtime behavior change in this phase.** Every code edit is documentation or a `log.info()` line. If a behavior change is needed, stop and revise the spec.
- **No deletes of any device module in this phase.** Even if you "know" a module is dead, wait for Phase 4 — the audit log is the evidence.
- **Do not introduce a new logger.** Reuse the existing `log` in `devices/base.py`. A new logger means a new entry in `manifest.json`'s `loggers` array, which is Phase 4's concern.
- **`UPSTREAM.md` is markdown, not a Python module.** Do not import it, do not parse it. It exists for humans.
