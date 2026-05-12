---
status: in_progress
phase: 4
feature: abode-fork-modernization
title: Observability, audit-driven deletes, and final cleanup
---

# Phase 4: Observability, Audit-Driven Deletes, and Final Cleanup

Surface two SocketIO health counters via the existing `diagnostics.py` path, add a structured DEBUG log per connect attempt, ingest the Phase 1 audit log to delete any provably-unregistered device modules, refresh `docs/ARCHITECTURE.md` for the post-lomond world, and run the full local + CI verification sweep that closes both [#62](https://github.com/molant/abode-security/issues/62) and [#61](https://github.com/molant/abode-security/issues/61).

## Context

Phase 3 left the SocketIO client byte-for-byte equivalent to the lomond version at every observable event boundary — same events, same log lines, same reconnect cadence. That was deliberate: keeping the diff focused on the transport swap. Phase 4 is the polish phase that pays off the "observability upgrade" choice from spec discovery and the "exploratory pruning" choice from the dynamic-discovery audit.

This phase has the smallest blast radius of any phase in this spec (no behavior change visible from `event_controller.py` upward) but the largest documentation impact.

Read [./README.md](./README.md) for the spec's stated observability goals and the dynamic-discovery surface explanation. Read [./phase-1-fork-hygiene.md](./phase-1-fork-hygiene.md) for the audit-log format that this phase ingests, and follow the repository guidance in `CLAUDE.md` for HA-integration edits.

## Structure

```
custom_components/abode_security/
  diagnostics.py                # update: add last_packet_age_seconds + consecutive_connect_failures
  abode/
    socketio.py                 # update: expose two read-only properties for the counters; one new DEBUG log line
    devices/                    # delete: any module that did not appear in Phase 1's audit log
docs/
  ARCHITECTURE.md               # update: SocketIO section reflects async aiohttp; drop "(lomond)" parenthetical
custom_components/abode_security/abode/UPSTREAM.md
                                # update: record any deletions from this phase
```

## Implementation Checklist

> Update these checkboxes as you complete each task!

### Baseline test verification (before starting implementation)

- [x] Run `./scripts/check.sh` — clean.
- [x] Run `uv run pytest -m integration` — all 104 items green.
- [x] Run `uv run pytest tests/test_pkg_import_audit.py` and `tests/test_abode_websocket.py` — green.
- [x] Run `uv run pytest tests/test_socketio_reconnect.py` — the async reconnect contract suite is green, including any Phase 3 shutdown coverage that was placed there.
- [x] **Locate the Phase 1 audit log.** Pull the most recent green integration-test log; grep for `abode_security.audit.registered_device_classes=` and record the comma-separated list in the PR description before starting deletions.

### Sub-Phase 4A: Expose health counters on `SocketIO`

The values exist already as private attributes inside `socketio.py`:

- `_last_packet_time` (a `datetime.datetime`).
- `_connect_failures` (an `int`).

Surface them as read-only properties with stable, snake_case public names so `diagnostics.py` can read them without breaking encapsulation.

- [x] In `socketio.py`, add:
  ```python
  @property
  def consecutive_connect_failures(self) -> int:
      return self._connect_failures

  @property
  def last_packet_age_seconds(self) -> float | None:
      if self._last_packet_time == datetime.datetime.min:
          return None
      return (datetime.datetime.now() - self._last_packet_time).total_seconds()
  ```
- [x] Add `tests/test_socketio_diagnostics.py` with a focused property test that constructs a `SocketIO`, asserts `consecutive_connect_failures == 0` and `last_packet_age_seconds is None` before any packet, then sets `_last_packet_time = datetime.datetime.now() - timedelta(seconds=42)` and asserts `40 <= last_packet_age_seconds <= 45`.
- [x] Run `./scripts/check.sh` — clean.

### Sub-Phase 4B: Surface counters in `diagnostics.py`

`diagnostics.py` already builds a redacted diagnostics payload returned by HA's diagnostics API. Add the two new fields under a `"socketio"` key.

- [x] In `custom_components/abode_security/diagnostics.py`, locate the existing payload construction. The relevant object walk is `abode_system.abode.events._socketio`: `abode.events` is the `EventController` instance, and its `_socketio` attribute is the `SocketIO` instance. Use this walk:
  ```python
  socketio_inst = getattr(
      getattr(abode_system.abode, "events", None),
      "_socketio",
      None,
  )
  if socketio_inst is not None:
      payload["socketio"] = {
          "consecutive_connect_failures": socketio_inst.consecutive_connect_failures,
          "last_packet_age_seconds": socketio_inst.last_packet_age_seconds,
      }
  ```
  Each level is `getattr`-guarded because the diagnostics handler is called even on partially-set-up entries (e.g. config flow failed before `events` was constructed). Returning `null`/missing rather than raising matches the existing handler's defensive style: the current sections already fall back instead of letting attribute-shape errors escape. Do NOT dereference unconditionally — diagnostics must not crash for unconfigured entries.
- [x] Extend `tests/test_diagnostics.py` with exact payload assertions:
  - when `events._socketio.consecutive_connect_failures = 3` and `events._socketio.last_packet_age_seconds = 4.2`, diagnostics includes `"socketio": {"consecutive_connect_failures": 3, "last_packet_age_seconds": 4.2}`;
  - when `events` or `events._socketio` is absent, diagnostics still returns successfully and omits the `"socketio"` block rather than raising.
- [x] These counters are public-state-of-the-system, not credentials. Do not add them to the redaction list.
- [x] Run `./scripts/check.sh` — clean.

### Sub-Phase 4C: Add one structured DEBUG log per connect attempt

The current `socketio.py` already logs `"Attempting to connect to SocketIO server..."` at INFO. Add a sibling DEBUG line carrying the structured context that incident triage needs.

- [x] Inside `_run()`, at the top of each iteration, after the existing `log.info("Attempting to connect to SocketIO server...")`, add:
  ```python
  log.debug(
      "abode_security.socketio.connect_attempt attempt=%d last_packet_age=%s",
      self._connect_failures + 1,
      self.last_packet_age_seconds,
  )
  ```
  Note the `last_packet_age_seconds` access — Sub-Phase 4A made it a property.
- [x] No test required for a single DEBUG log line; verify manually by running an integration test with `LOG_LEVEL=DEBUG` and grepping for `abode_security.socketio.connect_attempt`.
- [x] Do NOT remove or rephrase the existing INFO `"Attempting to connect to SocketIO server..."` line. See README → "Invariants" — existing log lines are stable.

### Sub-Phase 4D: Ingest the Phase 1 audit log and delete provably-unregistered device modules

Phase 1 emitted `abode_security.audit.registered_device_classes=<comma-list>` during integration tests. Compare that list to the filesystem.

- [x] Run `ls custom_components/abode_security/abode/devices/*.py | xargs -n1 basename | sed 's/.py$//' | sort` and note the device-module names. Subtract `__init__`, `base`, `_ancestry`, `pkg`, `status` from the list — those are infrastructure, not concrete `Device` subclasses, and will not appear in the audit.
- [x] Diff the remaining list against the audit-log output. **Only modules that BOTH (a) are absent from the audit AND (b) are not imported by any `custom_components/abode_security/*.py` file are deletion candidates.**
- [x] For each candidate:
  - `git rm custom_components/abode_security/abode/devices/<name>.py`.
  - Search for the module name across the repo (`grep -rn "<name>" custom_components/ tests/ --include="*.py"`) to confirm zero post-delete references.
  - Update `UPSTREAM.md`'s "Intentional divergence" section: add a line "Deleted unused device module `<name>.py` (not registered by `pkg.import_all()` during integration tests; not imported anywhere)."
- [x] **If no candidates exist** (the audit registers everything in `devices/`): add a sentence to `UPSTREAM.md` recording the audit result for future contributors: "Integration-test audit on <date> registered every device module under `devices/`. No modules are dead weight." This is a positive result — record it.
- [x] Re-run baseline tests after any delete. `uv run pytest -m integration` must remain green.

### Sub-Phase 4E: Update `docs/ARCHITECTURE.md`

The SocketIO section currently references lomond and the daemon-thread model. Refresh it.

- [x] Locate the SocketIO section. Update the protocol-stack bullet from `"WebSocket (lomond) → EngineIO → SocketIO"` to `"WebSocket (aiohttp) → EngineIO → SocketIO"`.
- [x] Update any prose describing the daemon-thread + `run_coroutine_threadsafe` bridge. Replace with a brief description of the async-task-on-HA-loop model. Reference `docs/ASYNC_AWAIT_PATTERNS.md` for the broader pattern; keep ARCHITECTURE.md short.
- [x] Add a "Where to look first when SocketIO is unhappy" cross-reference: `diagnostics.py`'s `"socketio"` keys; `mcp__home_assistant__ha_get_logs` filtered by `custom_components.abode_security`; the integration `tests/test_socketio_reconnect.py` for the contract.

### Sub-Phase 4F: Close the spec and the issues

- [ ] Set `status: done` in this file's frontmatter.
- [ ] Set `status: done` in `README.md`'s frontmatter.
- [ ] In the PR body that ships Phase 4, include: `Closes #62` and `Closes #61`. (Earlier-phase PRs reference these issues but should not auto-close them.)
- [ ] After PR merge, run `/spec-done features/abode-fork-modernization` to archive the spec folder.

### Documentation (end of phase)

- [ ] `docs/ARCHITECTURE.md` — updated in Sub-Phase 4E.
- [ ] `UPSTREAM.md` — updated in Sub-Phase 4D (audit outcome + any deletes).
- [ ] `CLAUDE.md` (root of this subproject) — review for any references to `lomond` or the threading model; remove if found. (Spot-check; likely nothing to change.)

### Build verification (required before marking phase complete)

- [ ] `./scripts/check.sh` — clean.
- [ ] `uv run pytest` — full unit suite green; expect the new `tests/test_diagnostics.py` payload assertions and the required `tests/test_socketio_diagnostics.py` property test added in Sub-Phase 4A.
- [ ] `uv run pytest -m integration` — all integration items green. If Sub-Phase 4D deleted modules, the count may decrease by the number of parametrized cases for those device types — note the new count in the PR description.
- [ ] `grep -rn "lomond" custom_components/ tests/ docs/` — zero hits outside `UPSTREAM.md`'s historical record and this spec.
- [ ] `grep -rn "threading" custom_components/abode_security/abode/socketio.py` — zero hits. (Note: `event_controller.py` still imports `threading` for its `_callback_lock` RLock and `_connection_lock` Lock — those are unrelated to the in-flight-future tracking removed in Phase 3B and stay.)
- [ ] `grep -rn "run_coroutine_threadsafe" custom_components/abode_security/` — zero hits.
- [ ] Run `mcp__home_assistant__ha_get_logs` filtered to the integration. The new `abode_security.socketio.connect_attempt` DEBUG line should appear during reconnect cycles when DEBUG is enabled; should be absent at INFO.
- [ ] Mark this file's frontmatter `status: done` only after every box above is checked.

### Manual verification with MCP tools (if available)

- [ ] `mcp__home_assistant__ha_call_service` with `homeassistant.diagnostics` (or whatever HA exposes for diagnostics fetch — fall back to the Settings → Devices & Services → Abode Security → Download Diagnostics flow if MCP doesn't expose it). Confirm the downloaded payload contains the new `"socketio"` sub-dict with both counters.
- [ ] `mcp__home_assistant__ha_get_history` over a 10-minute window that includes a forced reconnect: confirm entities update through the reconnect and the counters in `diagnostics.py` reflect the disturbance.

## Technical Details

### Diagnostic payload shape (target)

After Phase 4, a diagnostics download includes:

```json
{
  "...existing fields...": "...",
  "socketio": {
    "consecutive_connect_failures": 0,
    "last_packet_age_seconds": 4.2
  }
}
```

`last_packet_age_seconds` is `null` (Python `None`) when no packet has ever been received (initial state, before first SocketIO `text` event). Surfacing `null` rather than a sentinel like `-1` lets the consumer distinguish "we haven't connected yet" from "we connected and haven't received anything in 0 seconds."

### Why these two counters specifically

These two values are the high-signal-to-noise summary of SocketIO health. Picked over alternatives during scope discovery because:

- **`consecutive_connect_failures`** already drives the `persistent_disconnect` event at threshold=20. Exposing it via diagnostics gives an operator a number to compare against the threshold during triage.
- **`last_packet_age_seconds`** detects the "connected but silent" failure mode — a TCP connection that's open and not erroring but is no longer receiving Abode events. The existing ping-timeout logic eventually trips on this, but a diagnostics download catches it earlier.

Other counters considered and rejected:

- Total bytes / packet rate — useful but high-frequency; better suited to a metrics export than a diagnostics snapshot.
- Last ping latency — already implicit in the ping-timeout log warnings; redundant.

### Audit-delete decision rule (worked example)

Suppose Phase 1's audit log shows:

```
abode_security.audit.registered_device_classes=...alarm,binary_sensor,camera,cover,light,lock,sensor,switch,valve
```

And `ls devices/*.py | xargs -n1 basename | sed 's/.py$//' | sort` returns:

```
__init__ _ancestry alarm base binary_sensor camera cover light lock pkg sensor status switch valve
```

After subtracting infrastructure (`__init__`, `_ancestry`, `base`, `pkg`, `status`), the concrete-device candidates are:

```
alarm binary_sensor camera cover light lock sensor switch valve
```

Diffed against the audit, every concrete device is registered. Outcome: no deletes. Record this in `UPSTREAM.md` and move on.

If `valve` had been missing from the audit, and `grep -rn "valve" custom_components/abode_security/ --include="*.py"` showed no imports from the outer integration, then `valve.py` would be a deletion candidate.

### Test impact of any deletes

If a device module is deleted, parametrized tests that iterate over device types may decrease in collected count. Update the PR description with the before/after count. Do not modify test parametrization to "preserve" the old count — let it shrink naturally.

## Constraints

- **No behavior change visible above `event_controller.py`.** The new counters are read-only properties; the new log line is DEBUG only; existing log lines are unchanged.
- **`null` is the correct value for `last_packet_age_seconds` before the first packet.** Do not substitute `0`, `-1`, or any other sentinel.
- **Audit-delete decisions are bounded by the audit log AND a grep.** Both conditions must be true to delete. A module being absent from the audit but imported elsewhere stays.
- **Do not change the diagnostics redaction list.** The new counters are not credentials; they go into the payload unredacted.
- **If Sub-Phase 4D deletes nothing, that is a successful outcome.** Record the audit-verified registration list in `UPSTREAM.md` and proceed.
- **Do not introduce a metrics-export framework.** This phase adds two values to a snapshot, not a Prometheus exporter. The metrics-vs-diagnostics decision was made during scope discovery — see README → "Out of scope".
