---
status: done
phase: 3
feature: abode-fork-modernization
title: SocketIO async refactor and lomond removal
---

# Phase 3: SocketIO Async Refactor and Lomond Removal

Rewrite `custom_components/abode_security/abode/socketio.py`'s `SocketIO` class as an async-native coroutine on the HA event loop, using the `AbodeWebSocket` wrapper from Phase 2 as its transport. Drop the four `asyncio.run_coroutine_threadsafe()` bridge sites in `event_controller.py`. Remove `lomond` from `manifest.json` requirements and loggers. The contract under test stays the same; only the implementation underneath changes.

This is the meat of the project. The diff will be large; the behavior change must be **zero** at the integration test boundary.

## Context

Today, `socketio.py:SocketIO.start()` spawns a `threading.Thread(target=self._run, name="SocketIOThread", daemon=True)`. That thread runs the reconnect loop, talks to `lomond.WebSocket` synchronously inside `lomond.persist()`, and dispatches events through `_handle_event()` callbacks. Those callbacks invoke registered handlers on the SocketIO thread. `event_controller.py` then bounces several of them back to the HA loop with `asyncio.run_coroutine_threadsafe()`.

After Phase 3:

- `SocketIO.start()` spawns `asyncio.create_task(self._run())`.
- `_run()`, `_step()`, and all framing handlers are `async def`.
- `_handle_event()` awaits async callbacks directly. Sync callbacks still work (called inline).
- `event_controller.py` drops the `run_coroutine_threadsafe` bridge — its callbacks register as `async def` and run directly on the HA loop.
- `lomond` is no longer imported anywhere. `manifest.json` is updated.

The wire format on the EngineIO/SocketIO layer is unchanged byte-for-byte.

Read [./README.md](./README.md) (especially the "Invariants the refactor must preserve" section) before starting, and follow the repository guidance in `CLAUDE.md` for HA-integration edits.

### Phase 2 wrapper contract (recap for fresh sessions)

If you arrive here without Phase 2's context in memory, the `AbodeWebSocket` wrapper at `custom_components/abode_security/abode/_websocket.py` exposes:

```python
class AbodeWebSocket:
    def __init__(self, url: str, *, cookie: str | None = None, origin: str | None = None) -> None: ...

    @property
    def closed(self) -> bool: ...

    async def connect(self) -> None:
        """Open the WebSocket. Raises AbodeWebSocketError on failure."""

    async def send_text(self, data: str) -> None:
        """Send a text frame. Raises AbodeWebSocketError if not connected."""

    async def receive(self) -> AsyncIterator[tuple[aiohttp.WSMsgType, str]]:
        """Async generator. Yields (WSMsgType.TEXT, str) tuples; stops on CLOSE/CLOSED;
        raises AbodeWebSocketError on ERROR or transport failures already mapped by
        the wrapper."""

    async def close(self) -> None:
        """Idempotent."""


class AbodeWebSocketError(Exception): ...
```

Use the wrapper exactly: pass `cookie` and `origin` at construction, `await connect()`, iterate `async for (msg_type, text) in ws.receive()` (note: `receive()` is an `async def` returning an async generator — you call it then iterate, **not** `async for msg in ws.receive` without parentheses), and `await close()` in cleanup. Catch `AbodeWebSocketError` (not `aiohttp.ClientError` — the wrapper has already mapped those).

## Structure

```
custom_components/abode_security/abode/
  socketio.py                   # update: SocketIO class → async; remove lomond imports
  event_controller.py           # update: drop 4 run_coroutine_threadsafe sites; callbacks → async; EventController.stop() becomes async
  UPSTREAM.md                   # update: move lomond from "deps" to "removed" in Intentional Rewrites
custom_components/abode_security/
  manifest.json                 # update: remove "lomond" from requirements and loggers
  __init__.py                   # update: callers of events.stop() add `await` (async_unload_entry path)
tests/
  test_socketio_reconnect.py    # update: mechanical sync → async on the 8 existing tests
  conftest.py                   # update only if SocketIO fixtures need re-shaping
```

## Implementation Checklist

> Update these checkboxes as you complete each task!

### Baseline test verification (before starting implementation)

- [x] Run `./scripts/check.sh` — clean.
- [x] Run `uv run pytest -m integration` — all 104 items green.
- [x] Run `uv run pytest tests/test_socketio_reconnect.py` — 8 tests green (these are the contract).
- [x] Run `uv run pytest tests/test_abode_websocket.py` — 11 tests green (Phase 2 baseline).
- [x] Confirm Phase 1 audit log is still being produced: `grep "abode_security.audit.registered_device_classes" <recent integration-test log>`. Phase 4 uses this; it must keep working through Phase 3.

### Sub-Phase 3A: Rewrite `SocketIO` as async (TDD, RED → GREEN)

Start with the existing tests in `tests/test_socketio_reconnect.py`. Convert them mechanically so they exercise the async API. Run them — they will fail because the implementation is still sync. That's the RED step.

- [x] For each of the 8 test methods in `tests/test_socketio_reconnect.py`:
  - Add `@pytest.mark.asyncio` decorator.
  - Change `def test_...` → `async def test_...`.
  - Add `await` in front of every call to `socketio.stop()` and `socketio._step()`. `socketio.start()` stays a regular scheduling method.
  - Replace any `threading.Event` assertions with task-state assertions (`task.done()`, `task.cancelled()`).
  - The assertions on `_cookie`, `_connect_failures`, `_persistent_disconnect_fired`, `_callbacks`, and the `BackoffIntervals` distribution **do not change** — those state checks are still valid.
- [x] Run `uv run pytest tests/test_socketio_reconnect.py -v` — expect failures because the tests now await async APIs that the implementation has not provided yet. Do not lock the RED step to one exact exception shape; the failure details depend on which methods were converted first.
- [x] Rewrite `socketio.py`'s `SocketIO` class:
  - `start()` becomes a regular method (not async) that calls `asyncio.create_task(self._run())` and stores the task handle. Returning a non-coroutine matches lomond's old behavior; callers don't need to `await` it.
    - Rationale for not-async-start: avoids forcing every existing `client.start()` call site to become async. The pattern matches HA's coordinator `async_setup` shape.
    - **Precondition**: `asyncio.create_task` requires a running event loop. Today, `EventController` already validates `self._event_loop.is_running()` before scheduling startup work. Either preserve that guard at the `SocketIO.start()` callsite, or call `asyncio.get_running_loop()` inside `start()` and let it raise `RuntimeError` early if mis-called. Do NOT swallow that error — a silent no-op on a missing loop is the bug that breaks the integration cold-start.
    - Today, `self._thread = None` is the "not started" sentinel and `if self._thread: return` is the idempotency guard in `start()`. Replace with `self._task: asyncio.Task | None = None` and `if self._task is not None and not self._task.done(): return`. The `done()` check matters — if a prior `_run()` exited cleanly, a fresh `start()` should be able to restart.
  - `stop()` becomes `async def stop()`. It sets the exit flag and awaits the running task with `asyncio.wait_for(task, timeout=10.0)`. Only if that graceful wait times out does it log the warning, cancel the stuck task, and best-effort drain the cancellation. This preserves today's `thread.join(timeout=10)` shutdown shape instead of making every stop an eager cancellation.
  - `_run()` becomes `async def _run()`. Same outer `while self._running:` loop. The wait between iterations replaces `threading.Event.wait(interval)`. The semantics flip is the canonical place to mis-implement: `threading.Event.wait(timeout)` returns `True` when set (i.e. "stop received → break") and `False` on timeout (i.e. "interval elapsed → continue"). The asyncio equivalent signals timeout via exception, not return value. Write it exactly like this:
    ```python
    try:
        await asyncio.wait_for(self._exit_event.wait(), timeout=interval)
        # Reached here only if .set() was called — caller wants to stop.
        break
    except TimeoutError:
        # Interval elapsed normally; continue the outer loop.
        pass
    ```
    Do NOT write this as `if await asyncio.wait_for(...): break` — `asyncio.Event.wait()` only completes (returns `True`) when `.set()` is called; the timeout is signalled via the exception. The `TimeoutError` in the example is the **expected** path, not the error path.
    - `_exit_event` becomes `asyncio.Event` (not `threading.Event`).
    - Do not introduce a bare `except Exception:` here — that would swallow `asyncio.CancelledError` from `stop()`.
  - `_step()` becomes `async def _step()`:
    - Cookie wait stays as a poll loop, but uses `asyncio.sleep(0.05)` and checks `_exit_event.is_set()` between polls. Keep the 15s ceiling (300 polls × 50ms). After the wait succeeds, **re-clear and re-check `_running`** to preserve the existing stop-races-with-clear guard (`self._exit_event.clear()` followed by `if not self._running: raise SocketIOException(...)`).
    - Instantiate `AbodeWebSocket(self._url, cookie=self._cookie, origin=self._origin)` instead of `lomond.WebSocket(...)`. `await ws.connect()` — wrap `AbodeWebSocketError` as `SocketIOException(ERRORS.SOCKETIO_ERROR, details=str(exc))`.
    - **After `await ws.connect()` succeeds, call `intervals.reset()` and then `await self._on_websocket_connected(None)` explicitly.** Backoff reset stays in `_step` (matches today's `if isinstance(event, events.Connected): intervals.reset()` inside the persist loop — `intervals` is a `_step`-local, not a `SocketIO` attribute, so the handler can't own it). Then `_on_websocket_connected` resets `_connect_failures`, fires `connection_recovered`, and dispatches `"connected"`. Do NOT skip the handler by inlining `await self._handle_event("connected")` only — that loses the counter resets.
    - The `for event in persist(...)` loop becomes `async for msg_type, text in self._websocket.receive()`. The frame dispatcher is a small async loop that:
      - On `WSMsgType.TEXT`: call `await self._on_websocket_text(text)` (note: the new signature takes the raw text string, not a lomond `events.Text` object — see "`_on_websocket_*` signature change" below).
      - Detects "closed/error" via the iterator stopping or raising. After the iterator exits, await `self._on_websocket_disconnected(None)`.
      - Polls for `_last_packet_time` ping-timeout on a 5-second `asyncio.sleep` cadence (replaces lomond's `persist(..., poll=5.0)` behavior). Move this into a sibling task spawned with `asyncio.create_task` inside `_step()` and cancelled before returning. See [Polling-task pattern in `_step`](#polling-task-pattern-in-_step) for the cancellation/cleanup pattern (use `contextlib.suppress(asyncio.CancelledError)` around the awaited cancellation).
  - Every `_on_websocket_*`, `_on_engineio_*`, `_on_socketio_*` method becomes `async def`. Their bodies are unchanged except:
    - `self._websocket.send_text(...)` becomes `await self._websocket.send_text(...)`.
    - `self._websocket.close()` becomes `await self._websocket.close()`.
    - `self._handle_event(...)` becomes `await self._handle_event(...)` at **every** call site. Today there are at least 10 such call sites across `_run`, `_on_websocket_connected`, `_on_websocket_disconnected`, `_on_websocket_poll`, `_on_engineio_pong`, `_on_socketio_error`, `_on_socketio_event`, and the loop-exit `stopped` event — verify via `grep -n "_handle_event" custom_components/abode_security/abode/socketio.py` before and after.
    - **`_on_websocket_text` signature changes**: today it takes a lomond `events.Text` event and reads `_event.text`. After refactor it takes the raw `text: str` directly. Update the body: `code = int(text[:1]); message = text[1:]` (drop the `.text` accessor). The `log.debug("Received: %s", _event.text)` line becomes `log.debug("Received: %s", text)` — preserve the "Received:" prefix (used in incident triage).
    - **`_on_websocket_backoff` can be deleted** — lomond emitted `Backoff` events on its internal reconnect loop. After the refactor, backoff happens in `_run()` (outside `_step`), so no such event is dispatched. Confirm with a grep that nothing else references it.
  - `_handle_event()` becomes `async def`. For each callback in `self._callbacks[event_name]`: if `inspect.iscoroutinefunction(callback)`, `await callback(*args)`; else call inline. Wrap each call in the existing `try/except Exception` block that logs and continues. See [Inline async dispatch in `_handle_event`](#inline-async-dispatch-in-_handle_event) for the exact snippet.
  - **`_add_header` and `set_origin`/`set_cookie` lifecycle**: today `_add_header` calls `self._websocket.add_header(name.encode(), value.encode())` on lomond's `WebSocket` object after instantiation but before `persist()`. aiohttp's wrapper takes `cookie`/`origin` at construction time (Phase 2 API), so `_add_header` is no longer needed. **Delete `_add_header`**, **delete** the two `self._add_header(...)` calls, but **keep** `set_origin`/`set_cookie` (they mutate `self._origin` / `self._cookie` and are called externally by `event_controller.py` between iterations — confirm this by grepping `set_cookie` and `set_origin` across `event_controller.py` and tests).
  - `BackoffIntervals`, `find_json_list`, the `EngineIO`/`SocketIO` codes maps, and `PERSISTENT_DISCONNECT_THRESHOLD` are unchanged.
- [x] Add focused shutdown coverage to `tests/test_socketio_reconnect.py` for the new async contract. Prove:
  - `await stop()` returns without cancelling a task that exits after `_exit_event.set()`.
  - A task that ignores the exit event reaches the 10s timeout path, gets cancelled, and emits the existing warning text for the async-task variant.
  Keep these tests small by patching `asyncio.wait_for` / the task under test; do not sleep for real time.
- [x] Remove the three `lomond` imports from the top of `socketio.py`. After removal, `grep "lomond" custom_components/abode_security/abode/socketio.py` should produce no hits.
- [x] Map `WebSocketError` → `AbodeWebSocketError` in the outer `_run()` try/except. There is no longer a `lomond.errors.WebSocketError`; the catch becomes `except AbodeWebSocketError`. Log message stays the same string template so log alerts don't break: `"Websocket Error: %s"`.
- [x] Run `uv run pytest tests/test_socketio_reconnect.py -v` — the converted reconnect contract remains green, along with the shutdown coverage added in this phase.

### Sub-Phase 3B: Drop the EventController bridge

`event_controller.py` has four `asyncio.run_coroutine_threadsafe()` call sites today (verify via `grep -n "run_coroutine_threadsafe" custom_components/abode_security/abode/event_controller.py`). Each marshals work from the SocketIO thread onto the HA event loop. After Phase 3A, the SocketIO class fires callbacks directly on the HA loop, so the bridge is dead weight.

The four sites and the work they schedule:

| Method | Coroutine scheduled | Done-callback |
|---|---|---|
| `_on_socket_started` | `asyncio.wait_for(self._async_get_session(), timeout=LONG_OPERATION_TIMEOUT)` | `_on_session_init_done` |
| `_on_socket_connected` | `asyncio.wait_for(self._async_refresh(), timeout=LONG_OPERATION_TIMEOUT)` | `_on_refresh_done` |
| `_on_device_update` | `asyncio.wait_for(self._async_refresh_device_and_dispatch(devid), timeout=LONG_OPERATION_TIMEOUT)` | inline `_log_future_result` lambda |
| `_execute_callback` (module-level helper) | `_run_callback_async(callback, callback_args, kwargs)` | inline `_log_callback_completion` lambda |

For the first three methods (`_on_socket_started`, `_on_socket_connected`, `_on_device_update`):

- [x] Convert each method's signature: `def _on_socket_started(self)` → `async def _on_socket_started(self)`.
- [x] Replace the `asyncio.run_coroutine_threadsafe(...)` + `add_done_callback(...)` pattern with a direct `await asyncio.wait_for(coro, timeout=self.LONG_OPERATION_TIMEOUT)`. **Keep the timeout** — `LONG_OPERATION_TIMEOUT = 30` is a real design constraint (HA setup phase) and is not a threading artifact.
- [x] Fold the done-callbacks (`_on_session_init_done`, `_on_refresh_done`, and the `_log_future_result` lambda) into `try/except TimeoutError / asyncio.CancelledError / Exception` blocks inside the converted methods. Preserve the existing log messages verbatim (e.g. `"Session initialization timed out"`, `"Abode refresh timed out"`) — they are referenced by potential user log alerts (see README → "Invariants").
- [x] After the conversion, **delete** `_on_session_init_done` and `_on_refresh_done`. They're unreachable.
- [x] Keep the `_socketio.on(...)` registration block unchanged in shape (9 registrations, no count change). `_handle_event()` (now `async`) detects coroutine callbacks via `inspect.iscoroutinefunction` and `await`s them — see [Inline async dispatch](#inline-async-dispatch-in-_handle_event). Sync handlers (`_on_socket_disconnected`, `_on_persistent_disconnect`, `_on_connection_recovered`, `_on_mode_change`, `_on_timeline_update`, `_on_automation_update`) stay sync.

For `_execute_callback`:

- [x] **Do NOT delete `_execute_callback` blanket-style.** It is called from six places (verify via `grep -n "_execute_callback(" custom_components/abode_security/abode/event_controller.py`). What changes is its internals: today it uses `asyncio.run_coroutine_threadsafe` for the "bound HA-entity-method" branch. After Phase 3A the caller is already on the HA loop, so direct dispatch via `asyncio.create_task` is correct for the async path:
  ```python
  def _execute_callback(callback, *args, **kwargs):
      callback_args = args
      if args and isinstance(args[0], asyncio.AbstractEventLoop):
          # Strip event-loop first-arg for backwards-compat with sync callers
          # that still pass it (e.g. _on_device_update fallback path).
          callback_args = args[1:]
      try:
          if asyncio.iscoroutinefunction(callback):
              # Fire-and-forget; _execute_callback is called from sync event
              # handlers like _on_persistent_disconnect that can't await.
              task = asyncio.create_task(
                  _run_callback_async(callback, callback_args, kwargs)
              )
              task.add_done_callback(lambda t: _log_task_completion(callback, t))
          else:
              callback(*callback_args, **kwargs)
      except Exception as exc:
          log.error("Failed to execute callback: %s: %s", callback, exc)
  ```
  Keep completion/error logging for this fire-and-forget path. Replace `_log_callback_completion` with `_log_task_completion` that accepts an `asyncio.Task`, calls `task.result()` inside the same timeout/error handling pattern, and preserves the existing log messages. Without the done-callback, callback failures become easy-to-miss background task exceptions.

For the in-flight tracking machinery:

- [x] Delete `_track_inflight`, `_discard_inflight`, `_inflight_futures`, `_inflight_lock`. They exist specifically to shut down `run_coroutine_threadsafe` futures during `stop()`. Once all `run_coroutine_threadsafe` call sites are gone, there are no orphan `concurrent.futures.Future` instances to track. (Pending `asyncio.Task`s from the new `_execute_callback` are tracked by the running loop; HA's teardown cancels them via the normal task cleanup.)
- [x] Convert `EventController.stop()` to `async def stop(self)`. New body: `await self._socketio.stop()`. The `_inflight_lock` and the for-loop cancelling futures go away. `_callback_lock` (RLock) and `_connection_lock` (Lock) stay — they protect callback registries, unrelated to the in-flight bridge.
- [x] In `custom_components/abode_security/__init__.py`, update the `abode_system.abode.events.stop()` call sites (inside `async_unload_entry` and friends — verify with grep) to `await abode_system.abode.events.stop()`. They're already inside `async` functions, so only `await` is added.
- [x] **`set_event_loop` / `_event_loop` handling**: Today `EventController.set_event_loop(loop)` is called from outer setup (`__init__.py`) and stores the loop on `self._event_loop` so callbacks can `run_coroutine_threadsafe(coro, self._event_loop)`. After the refactor, all callbacks run on the current loop (`asyncio.get_running_loop()` returns the right one inside `await`-contexts), so storing it is no longer required for correctness. Two acceptable options:
  - **Option A (recommended)**: Keep `set_event_loop` and `_event_loop` as legacy hooks that tests still call. Stop dereferencing `_event_loop` in production code — the validation guards in `_on_socket_started` can stay but become advisory (downgrade `log.error` to `log.debug`).
  - **Option B**: Delete `set_event_loop`/`_event_loop` entirely and update the test fixture. Larger blast radius; do this only if you're also touching the test fixtures for other reasons.
  Choose A by default. Note your choice in the PR description.

Verification:

- [x] `grep -n "run_coroutine_threadsafe" custom_components/abode_security/abode/event_controller.py` returns 0 hits.
- [x] `grep -n "_inflight" custom_components/abode_security/abode/event_controller.py` returns 0 hits.
- [x] `grep -n "_track_inflight\|_discard_inflight" custom_components/abode_security/` returns 0 hits.
- [x] Run `uv run pytest tests/test_socketio_reconnect.py` — the 3 `TestEventControllerStartedSeeding` tests in particular exercise this bridge. **Test patch update required**: the test currently patches `asyncio.run_coroutine_threadsafe`. After the refactor that patch becomes a no-op. Remove the patch and let the converted `async def _on_socket_started` `await` the real `_async_get_session` against a mocked `_client._session`; this is the required version of the test.
- [x] Add an `_execute_callback` async-branch test to `tests/test_socketio_reconnect.py` beside the existing `EventController` coverage. It must prove the created task gets a done-callback and task failures are consumed/logged through `_log_task_completion`, rather than surfacing as unhandled background-task warnings.
- [x] Run `uv run pytest` — full unit suite green.

### Sub-Phase 3C: Remove `lomond` from `manifest.json`

- [x] In `custom_components/abode_security/manifest.json`:
  - `requirements`: drop `"lomond"`. Final value: `["platformdirs", "aiohttp"]`.
  - `loggers`: drop `"lomond"`. Final value: `["custom_components.abode_security"]`.
- [x] Verify no remaining `lomond` imports anywhere in the integration: `grep -rn "lomond" custom_components/abode_security/ tests/`. Expected: zero hits.
- [x] `pyproject.toml` does NOT list `lomond` (it lives in `manifest.json` for HA's installer). Confirm with `grep lomond pyproject.toml` — zero hits expected.

### Sub-Phase 3D: Update `UPSTREAM.md`

Phase 1 created `UPSTREAM.md` with an "Intentional rewrites" section that mentions the future lomond removal as a Phase 3 deferral. Update that section to past tense now that it's done.

- [x] In `custom_components/abode_security/abode/UPSTREAM.md`'s "Intentional divergence" section, change the lomond bullet from "(Phase 3, future)" wording to a present-tense statement: "`lomond` replaced by `aiohttp.ClientWebSocketResponse` (PR <number>). SocketIO daemon thread folded into the HA event loop."
- [x] Bump the "Local commits modifying this directory" count to the new value: `git log --oneline -- custom_components/abode_security/abode/ | wc -l`.

### Sub-Phase 3E: Integration verification

- [x] Run `uv run pytest -m integration` against `./scripts/dev.sh` — all 104 items green. Reconnect scenarios are the highest-risk surface; watch the test_action_manager and test_socketio_reconnect output carefully.
- [x] In `./scripts/dev.sh`, manually:
  - Confirm HA starts cleanly. `docker logs abode-security-ha-1 2>&1 | grep -E "SocketIO Connected|Websocket Connected"` should show the connect sequence.
  - Trigger a reconnect by `docker compose restart mock-abode`, then watch the logs for `"Attempting to connect to SocketIO server..."` → `"Waiting %f seconds before reconnecting..."` → `"Websocket Connected"`. The interval should respect the 5–30s jitter band.
  - Drive the persistent_disconnect path by keeping mock-abode down for ~5 minutes (20 attempts × jittered backoff). Confirm `"signaling persistent disconnect"` appears. Bring mock-abode back; confirm `connection_recovered` fires (look for the HA service or UI surface that listens for it).
- [x] Stop HA cleanly (`docker compose down`). Confirm no `SocketIO thread did not exit within 10s` warnings — the analog now reads "did not exit within 10s" on the async task. The warning must remain reachable in principle but should not fire during clean shutdown.

### Documentation (end of phase)

- [x] `docs/ARCHITECTURE.md` — Phase 4 owns the SocketIO-section rewrite. Do not edit it here. (Phase 3 leaves it momentarily stale; Phase 4 reconciles.)
- [x] `docs/ASYNC_AWAIT_PATTERNS.md` — add a sentence to the "Background tasks" / "Service handlers" section noting that the SocketIO client is now an `asyncio.create_task` on the HA loop, no longer a daemon thread. Keep it brief — the bulk of the design lives in this spec.
- [x] `UPSTREAM.md` — updated in Sub-Phase 3D.

### Build verification (required before marking phase complete)

- [x] `./scripts/check.sh` — clean. Pay attention to mypy/pyright errors around async signature mismatches — those are the canonical "you forgot an `await`" signal.
- [x] `uv run pytest` — full unit suite green.
- [x] `uv run pytest -m integration` — all 104 items green. Run **twice** in a row — async refactors are the canonical breeding ground for race conditions.
- [x] `grep -rn "lomond" custom_components/ tests/ docs/` — zero hits outside this spec and `UPSTREAM.md`'s historical record.
- [x] `grep -rn "run_coroutine_threadsafe" custom_components/abode_security/abode/` — zero hits.
- [x] `grep -rn "threading\." custom_components/abode_security/abode/socketio.py` — zero hits (Phase 3 removes both `threading.Thread` and `threading.Event`).
- [x] Capture a new Phase 1 audit log from this integration run; confirm `registered_device_classes` is unchanged from Phase 1's baseline (no device classes lost during refactor).
- [x] If `package-lock.json`, `pubspec.lock`, etc. changed, stage them. (Expected: none.)
- [x] Mark this file's frontmatter `status: done` only after every box above is checked.

### Manual verification with MCP tools (if available)

- [x] `mcp__home_assistant__ha_get_state` on `alarm_control_panel.abode_alarm` and a couple of sensor entities — confirm states match what the mock-server's SocketIO push emitted.
- [x] `mcp__home_assistant__ha_get_logs` filtered to the integration's logger; confirm no new errors or warnings appear vs. the Phase 2 baseline.
- [x] `mcp__home_assistant__ha_get_history` covering a reconnect window — entity-update timestamps should bracket the disconnect/reconnect gap; no entities should be stuck on stale state.

## Technical Details

### Cancellation model for `stop()`

```python
async def stop(self) -> None:
    """Stop the SocketIO async task. Bounded by 10s timeout."""
    if self._task is None:
        return

    log.info("Stopping SocketIO task...")
    self._running = False
    self._exit_event.set()

    try:
        await asyncio.wait_for(self._task, timeout=10.0)
    except TimeoutError:
        log.warning("SocketIO task did not exit within 10s; cancelling")
        self._task.cancel()
        # Best-effort drain of the cancel; if it takes longer, give up.
        try:
            await asyncio.wait_for(self._task, timeout=1.0)
        except (TimeoutError, asyncio.CancelledError):
            pass
    finally:
        self._task = None
```

The 10s ceiling preserves the existing `thread.join(timeout=10)` semantics. The "did not exit within 10s" warning is reachable on a stuck task, matching today's "did not exit within 10s; abandoning" log.

### Inline async dispatch in `_handle_event`

```python
import inspect

async def _handle_event(self, event_name: str, *args: Any) -> None:
    for callback in self._callbacks[event_name]:
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as exc:
            log.exception("Captured exception during SocketIO event callback: %s", exc)
```

`inspect.iscoroutinefunction` is the supported, fast way to detect this. Caching the classification per-callback is premature optimization; the dispatch hot path is microseconds.

### Polling-task pattern in `_step`

Replacing `lomond.persist(..., poll=5.0, ping_rate=0)`'s combined "drain frames + emit a poll event every 5s" semantics. **Key invariant**: today, `_on_websocket_connected(events.Connected)` is invoked by lomond when the handshake completes, and that handler does the connect-side bookkeeping (`intervals.reset()`, reset `_connect_failures`, fire `connection_recovered` if the prior cycle had emitted `persistent_disconnect`, fire `connected`). Reproduce that chain exactly — do NOT inline a partial subset:

```python
async def _step(self, intervals: BackoffIntervals) -> None:
    await self._handle_event("started")
    await self._wait_for_cookie()       # the 15s poll/timeout, async version

    # Cleared-and-rechecked guard against stop() racing with the cookie wait.
    self._exit_event.clear()
    if not self._running:
        raise SocketIOException(
            ERRORS.SOCKETIO_ERROR,
            details="SocketIO stopped before WebSocket connect",
        )

    self._websocket = AbodeWebSocket(
        self._url, cookie=self._cookie, origin=self._origin,
    )
    try:
        await self._websocket.connect()
    except AbodeWebSocketError as exc:
        raise SocketIOException(ERRORS.SOCKETIO_ERROR, details=str(exc)) from exc

    # Reset the backoff schedule here (matches today's `if isinstance(event,
    # events.Connected): intervals.reset()` inside the persist loop).
    intervals.reset()

    # Drive the full _on_websocket_connected handler — it owns the connect
    # bookkeeping (counter reset, persistent-disconnect/recovery transitions,
    # `connected` event). Do not inline a partial version.
    await self._on_websocket_connected(None)

    poll_task = asyncio.create_task(self._poll_loop())
    try:
        async for msg_type, text in self._websocket.receive():
            await self._on_websocket_text(text)
    except AbodeWebSocketError as exc:
        # The outer _run() catches this; just let it propagate.
        log.warning("Websocket Error: %s", exc)
        raise
    finally:
        poll_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await poll_task
        await self._websocket.close()
        await self._on_websocket_disconnected(None)


async def _poll_loop(self) -> None:
    """Replaces lomond.persist(poll=5.0)'s 5s ping/timeout cadence.

    Runs in parallel with the receive() iterator. Cancelled by _step()
    when the connection ends. Keep exactly one reader task; aiohttp permits
    other tasks to send asynchronously on the same WebSocket.
    """
    while True:
        await asyncio.sleep(5.0)
        await self._on_websocket_poll(None)
```

Notes:
- The `raise` in the except block ensures that a transport error inside the receive loop propagates to `_run()` so the reconnect counter increments (today this is implicit via lomond's `WebSocketError` propagation). The `finally` block still runs cleanup.
- `_on_websocket_poll` may call `self._websocket.close()` internally on ping-timeout. After Phase 2 wrapper changes, `close()` is now `async`; ensure the body is updated: `await self._websocket.close()`.
- The `_poll_loop` is intentionally NOT collapsed into the main `async for` body. Doing so (e.g. with `asyncio.wait_for(self._websocket.receive(), timeout=5.0)`) would serialize the 5s tick with receive(), so a high-frequency event stream would starve the ping/timeout check.

### Test mocking after the refactor

The 8 existing tests in `tests/test_socketio_reconnect.py` already stub `BackoffIntervals.__next__` to return 0 (no sleep). That stub still works for the async version. The tests that monkeypatch `_step` must update to patch with an `AsyncMock` instead of a `MagicMock`. Example:

```python
# before:
monkeypatch.setattr(s, "_step", MagicMock(side_effect=SocketIOException(...)))

# after:
monkeypatch.setattr(s, "_step", AsyncMock(side_effect=SocketIOException(...)))
```

The existing 8 reconnect tests remain the primary behavioral contract, but Phase 3 also adds the narrowly-scoped shutdown and `_execute_callback` task-completion tests called out above. Those cover async failure modes that the pre-refactor suite cannot represent.

### `manifest.json` final state

```json
{
  "domain": "abode_security",
  "name": "Abode Security",
  "codeowners": ["@molant"],
  "config_flow": true,
  "documentation": "https://github.com/molant/abode-security",
  "issue_tracker": "https://github.com/molant/abode-security/issues",
  "homekit": {
    "models": ["Abode", "Iota"]
  },
  "iot_class": "cloud_push",
  "loggers": ["custom_components.abode_security"],
  "requirements": ["platformdirs", "aiohttp"],
  "single_config_entry": true,
  "version": "1.0.0-dev-...",
  "minimum_home_assistant_version": "2024.1.0",
  "diagnostics": true
}
```

The `version` string bumps automatically via the existing release process — do not hardcode a value in this PR.

## Constraints

- **EIO=3 is locked.** The URL still reads `?EIO=3&transport=websocket`. Do not change it. See README → "Concepts → EngineIO version (EIO=3, permanent)".
- **BackoffIntervals 5–30s and `PERSISTENT_DISCONNECT_THRESHOLD = 20` are tuned. Do not change them.**
- **Preserve `connection_recovered`, `persistent_disconnect`, `started`, `connected`, `disconnected`, and `stopped` event names byte-for-byte.** These are subscribed by `event_controller.py` and possibly by user-facing alerts.
- **Preserve all existing log line text** in `socketio.py` (`"Attempting to connect to SocketIO server..."`, `"Websocket Connected"`, `"SocketIO Server Ping Timeout"`, etc.). Users may have log-based alerts keyed on these. Phase 4 may add NEW lines; this phase must not change EXISTING ones.
- **No new runtime dependencies.** `aiohttp` is already in `manifest.json`. Do not add `websockets`, `python-socketio`, or anything else.
- **No mock-server changes.** The handshake fix from [#105](https://github.com/molant/abode-security/issues/105) (pinning `python-socketio==4.6.1` / `python-engineio==3.14.2`) stays. The client speaks EIO=3, the server is pinned to EIO=3 — they match.
- **Run integration tests twice consecutively before marking the phase done.** Async refactors are the canonical breeding ground for first-run-passes / second-run-races. If the second run fails, debug before claiming completion.
