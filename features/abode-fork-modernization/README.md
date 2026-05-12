---
status: pending
feature: abode-fork-modernization
title: Vendored abode/ fork modernization + lomond replacement
phases: 4
issues: [62, 61]
---

# Abode Fork Modernization (closes #62 and #61)

## Status

**Pending** — spec committed on `docs/abode-fork-modernization-spec`,
implementation not started. Bundled with [#61](https://github.com/molant/abode-security/issues/61)
because the lomond replacement reshapes the same files the fork-policy
decision in [#62](https://github.com/molant/abode-security/issues/62)
governs. Adjacent context lives in [#105](https://github.com/molant/abode-security/issues/105)
(why EIO=3 is permanent) and [#77](https://github.com/molant/abode-security/issues/77)
(why CI now actually exercises the SocketIO path).

## Goal

Document the vendored `custom_components/abode_security/abode/` fork's
lineage and divergence policy so future contributors know what we own,
then replace the unmaintained `lomond` WebSocket library inside it with
`aiohttp.ClientWebSocketResponse`, fold the SocketIO daemon thread onto
Home Assistant's event loop, and remove `lomond` from `manifest.json`.

Closes:
- **#62** — vendored `abode/` fork future (decision: hard divergence, no scheduled upstream sync)
- **#61** — replace unmaintained `lomond` WebSocket library

#61 is bundled into this spec because replacing `lomond` reshapes the
files the #62 policy decision applies to; doing them sequentially would
mean editing the same code twice.

## Why option C (and not A or B)

Issue #62 framed three resolution paths:

| | (A) keep fork honest | (B) re-extract as PyPI | (C) inline only what we use |
|---|---|---|---|
| Upstream sync | quarterly diff CI | npm-style release model | none |
| Maintenance cost | recurring | another package to ship | one-shot |
| Reachability audit | not required | not required | required to delete |
| Effort | ~2 hrs | ~1 week | 1–2 days for audit + lomond replacement |

(C) was chosen with one adjustment found during scope discovery:
**almost nothing in the fork is dead** because `devices/base.py` uses
dynamic class discovery (see [The actual mechanism](#the-actual-mechanism-dynamic-discovery--eio3)
below). So "inline what we use" effectively becomes "document the
fork, delete the one provably-dead artifact, audit the rest at
runtime, then do the real work — replace lomond."

For #61's library choice, three replacements were considered:

| | aiohttp.ClientWebSocketResponse | websockets library | python-socketio client |
|---|---|---|---|
| New runtime dep | none (already in manifest) | yes | yes |
| Async-native | yes | yes | yes |
| Owns EngineIO/SocketIO framing | no — we keep ours | no — we keep ours | yes — replaces socketio.py |
| Wire-version risk | none (we control framing) | none | high — v5 default; collides with EIO=3 (cf. #105) |

`aiohttp.ClientWebSocketResponse` won — it's already a transitive HA
dep declared in `manifest.json`, async-native, and leaves our
hand-rolled EngineIO/SocketIO framing alone so EIO=3 is not at the
mercy of an upstream client library's default version.

## The actual mechanism (dynamic discovery + EIO=3)

Two implementation details drive most of the spec; future readers need
both before any phase can be implemented safely.

**1. `pkg.import_all()` runs from `Device.new`, not at module import.**
`abode/devices/base.py` defines `Device.new(cls, state, client)` as a
classmethod. That classmethod calls `pkg.import_all()` **on every
invocation** — i.e. every time the integration constructs a Device
from a state dict. `pkg.import_all()` is idempotent (subsequent
imports are no-ops via `sys.modules`), but it is **not** a one-shot at
class-definition time. Once it has run, `_ancestry.iter_subclasses(Device)`
reveals every concrete `Device` subclass that registered as a side
effect of being imported. As a consequence, a device module's absence
from the outer integration's import list is **not** evidence that
it's dead — `valve.py`, `pkg.py`, `_ancestry.py` are all load-bearing
despite no direct outer-layer imports. Phase 1's audit must gate its
log on a module-level "logged once" sentinel; see
[Phase 1: Fork hygiene & audit](./phase-1-fork-hygiene.md) Sub-Phase 1C.

**2. EngineIO v3 is permanent.** The fork's SocketIO client speaks
EngineIO v3 (`?EIO=3&transport=websocket` in the URL). Upstream
`jaraco.abode` has hardcoded v3 for 2+ years; real Abode servers only
speak v3. Issue #105 was the mock-server's `python-socketio` v5 (EIO=4
default) rejecting the client's v3 handshake — fixed by pinning the
mock to `python-socketio==4.6.1` + `python-engineio==3.14.2`. The
refactor must preserve EIO=3 byte-for-byte. This is why
`python-socketio` was rejected as a replacement library: its v5
default would re-introduce exactly the same handshake mismatch we
just fixed.

## Implementation Phases

| Phase | File | Description | Status |
|-------|------|-------------|--------|
| 1 | [Phase 1: Fork hygiene & audit](./phase-1-fork-hygiene.md) | Add `UPSTREAM.md`. Delete `abode/artifacts/test-mode-requests`. Instrument `Device.new`'s `pkg.import_all()` (sentinel-gated) to log the registered class list during integration tests. No behavior change. | pending |
| 2 | [Phase 2: Async WebSocket transport scaffold](./phase-2-websocket-transport.md) | Add `abode/_websocket.py` — async wrapper over `aiohttp.ClientWebSocketResponse` — with 11 unit tests. No production callers wired up yet. | pending |
| 3 | [Phase 3: SocketIO async refactor](./phase-3-async-refactor.md) | Rewrite `socketio.py` `SocketIO` class as async on the HA loop. Drop `event_controller.py`'s `run_coroutine_threadsafe` bridge. Remove `lomond` from `manifest.json` requirements and loggers. | pending |
| 4 | [Phase 4: Observability + audit deletes + final cleanup](./phase-4-observability.md) | Add `last_packet_age_seconds` and `consecutive_connect_failures` to `diagnostics.py`. Ingest Phase 1's audit log; delete any provably-unregistered device modules. Refresh `docs/ARCHITECTURE.md`. | pending |

## Acceptance criteria

These are non-negotiable. Treat them as test assertions an
implementer should be able to point at, not preferences.

**Documentation**
- `custom_components/abode_security/abode/UPSTREAM.md` records the fork commit (`aee5d16`), fork date (2025-12-01), intentional deltas, and the no-automatic-sync policy.
- `docs/ARCHITECTURE.md`'s SocketIO section no longer parenthesizes "(lomond)"; it describes the async aiohttp transport.

**Transport (Phase 2 deliverable)**
- `abode/_websocket.py` exposes `async connect()`, `async send_text()`, `async receive()` (async-iterating `(WSMsgType, str)` frames), `async close()` (idempotent), and a `closed` property.
- `Cookie` flows via aiohttp's `headers=` argument; `Origin` flows via aiohttp's dedicated `origin=` kwarg. The two must not be conflated — aiohttp internally writes `headers[ORIGIN] = origin` after copying `headers`, and the dedicated kwarg is the idiomatic route.
- 11 unit tests under `tests/test_abode_websocket.py` pass.

**SocketIO refactor (Phase 3 deliverable)**
- `SocketIO.start()` stays a regular method (no `await` at call sites); `stop()`, `_run()`, `_step()`, and every `_on_*` handler become `async def`.
- `event_controller.py`'s four `asyncio.run_coroutine_threadsafe()` call sites (in `_on_socket_started`, `_on_socket_connected`, `_on_device_update`, `_execute_callback`) are gone; `grep -n run_coroutine_threadsafe custom_components/abode_security/abode/event_controller.py` returns 0 hits.
- `grep -n "threading\." custom_components/abode_security/abode/socketio.py` returns 0 hits.
- `manifest.json` `requirements` is `["platformdirs", "aiohttp"]`; `loggers` is `["custom_components.abode_security"]`.
- `tests/test_socketio_reconnect.py`'s 8 tests (4 in `TestPersistentDisconnect`, 1 in `TestCookieClearingBetweenIterations`, 3 in `TestEventControllerStartedSeeding`) stay green after mechanical sync→async edits (`@pytest.mark.asyncio`, `await`). Assertions themselves do not change.

**Preserved invariants (load-bearing — do not "modernize")**
- **EIO=3 in the URL**: `?EIO=3&transport=websocket`. See [The actual mechanism](#the-actual-mechanism-dynamic-discovery--eio3).
- **BackoffIntervals min=5, max=30, exponential jitter** — tuned for Abode's 429 rate-limit behavior; lower values get the integration IP-banned.
- **`PERSISTENT_DISCONNECT_THRESHOLD = 20`** consecutive failed cycles before `persistent_disconnect` fires.
- **`connection_recovered` event** fires on the first successful reconnect after a `persistent_disconnect`.
- **`stopped` event** fires once from `_run()` after the loop exits; outer cleanup hooks depend on it.
- **Cookie-wait 15s ceiling** at connect time (50ms × 300 polls); refactor keeps the poll-loop shape using `asyncio.sleep(0.05)` + `_exit_event.is_set()` checks.
- **`stop()` 10s bounded shutdown**: signal exit, await with timeout, cancel only if the task is stuck. Same ceiling, same warning path as today's `thread.join(timeout=10)`.

**Observability (Phase 4 deliverable)**
- `diagnostics.py` payload includes a `"socketio"` sub-dict with `consecutive_connect_failures` (int) and `last_packet_age_seconds` (float or null). Defensive `getattr` walk; absent block when `events` or `events._socketio` is unset.
- One new DEBUG log per connect attempt: `abode_security.socketio.connect_attempt attempt=N last_packet_age=<s>`.
- Every pre-existing INFO/WARNING log line in `socketio.py` survives verbatim (user log alerts may key on them).

## Out of scope

These were considered and explicitly declined during scope discovery — do not pull them into this spec mid-flight.

- **Ongoing upstream sync workflow.** No quarterly diff jobs, no scheduled re-sync. `UPSTREAM.md` records the policy and stops there.
- **Migration story for existing HA installs.** Transport swap with no schema/config changes; users upgrade in place.
- **Aggressive pruning of the fork.** Beyond deleting `abode/artifacts/test-mode-requests` and any device module the runtime audit proves is unregistered, the fork's module structure is untouched.
- **Re-extracting the fork as a PyPI package** (Option B from #62).
- **Rewriting the hand-rolled EngineIO/SocketIO framing.** The framing in `socketio.py` (the `EngineIO` codes map, `find_json_list`, `_on_engineio_*` / `_on_socketio_*` handlers) stays. Only the WebSocket transport underneath swaps.
- **Adopting `python-socketio` client.** Rejected for the EIO=3 reason above.
- **Replacing aiohttp with the `websockets` library.** Rejected to avoid adding a new runtime dep.

## TDD approach

Phase 1 has no failing-test target — it's documentation plus a
sentinel-gated log line, gated by `./scripts/check.sh` cleanliness and
the audit log appearing in the integration-test run.

Phase 2 is straight TDD: write the 11 unit tests in
`tests/test_abode_websocket.py` first (they fail with `ImportError`),
then implement the wrapper.

Phase 3 is TDD-on-invariants. The 8 existing tests in
[`tests/test_socketio_reconnect.py`](../../tests/test_socketio_reconnect.py)
are the contract. Convert them mechanically (add `@pytest.mark.asyncio`,
`await` the previously-sync calls), watch them fail against the still-sync
implementation, then rewrite the implementation until they pass again. The
assertions on `_cookie`, `_connect_failures`, `_persistent_disconnect_fired`,
`_callbacks`, and the `BackoffIntervals` distribution stay unchanged.
New tests in Phase 3 cover only the new async failure modes (graceful
vs timed-out `stop()`, `_execute_callback` task completion/error handling)
that the pre-refactor suite cannot represent.

Phase 4 adds focused unit tests for the diagnostic counters and the
`diagnostics.py` payload, plus a manual MCP-driven verification pass
through the live mock-server stack.

Integration tests (`pytest -m integration`, 104 collected items, gated
in CI since [#77](https://github.com/molant/abode-security/issues/77))
must remain green at the end of every phase. Async refactors are the
canonical breeding ground for first-run-passes / second-run-races —
Phase 3 specifically requires running the integration suite **twice
consecutively** before being marked done.
