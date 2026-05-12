---
status: done
phase: 2
feature: abode-fork-modernization
title: Async WebSocket transport scaffold
---

# Phase 2: Async WebSocket Transport Scaffold

Add a thin async-native WebSocket wrapper at `custom_components/abode_security/abode/_websocket.py`, backed by `aiohttp.ClientWebSocketResponse`. No production code calls it yet — this phase is pure scaffolding with unit tests so Phase 3 can wire it in without simultaneously inventing the transport API and rewriting `socketio.py`.

## Context

`socketio.py` today imports three symbols from `lomond`:

```python
from lomond import WebSocket, events
from lomond.errors import WebSocketError
from lomond.persist import persist
```

These three lines (and the threading model they imply) are the only `lomond` surface in the codebase. Replacing them in one PR alongside the SocketIO refactor would create a PR that touches transport API design AND the SocketIO class shape AND `event_controller.py`'s bridge code AND test fixtures — too much for a reviewable diff. Phase 2 isolates the transport-API design decision.

Read [./README.md](./README.md) for the public-surface requirements ("Transport" section) and the locked-in library choice (aiohttp).

## Structure

```
custom_components/abode_security/abode/
  _websocket.py                # new: async wrapper over aiohttp.ClientWebSocketResponse
tests/
  test_abode_websocket.py      # new: unit tests for the wrapper
```

The leading underscore in `_websocket.py` matches the fork's existing convention for internal helpers (`_itertools.py`, `_ancestry.py`, `_collections.py`).

## Implementation Checklist

> Update these checkboxes as you complete each task!

### Baseline test verification (before starting implementation)

- [x] Run `./scripts/check.sh` — clean.
- [x] Run `uv run pytest -m integration` — green.
- [x] Run `uv run pytest tests/test_pkg_import_audit.py` — green (Phase 1 baseline).

### Sub-Phase 2A: Define the wrapper interface (TDD, RED)

Write the tests first against the not-yet-existent module. They will fail with `ImportError`; that's the RED step.

- [x] Create `tests/test_abode_websocket.py`.
- [x] Write tests covering the public surface listed under [Technical Details — Public API](#public-api):
  - **Construction**: instantiating `AbodeWebSocket(url, cookie, origin)` does not open a connection.
  - **`connect()` round-trip**: with `aiohttp.ClientSession.ws_connect` mocked to return an `AsyncMock` ws, `await ws.connect()` issues `ws_connect(url, headers={"Cookie": cookie}, origin=origin, ...)` exactly once. **Note**: `aiohttp.ClientSession.ws_connect` exposes a dedicated `origin=` keyword alongside `headers=`. Use that kwarg — do **not** also put `Origin` into `headers`. `Cookie` has no dedicated WebSocket keyword, so it goes in `headers`.
  - **`connect()` omits values when None**: when constructed without a cookie, no `Cookie` key appears in `headers` (pass `headers=None` if it would otherwise be empty). When constructed without an origin, `origin=None` is passed (aiohttp's default; produces no `Origin` header).
  - **`send_text(s)` delegates to the underlying ws**: assert the mock ws's `send_str` is awaited once with the exact string.
  - **`receive()` yields TEXT frames as `(WSMsgType.TEXT, str)`**: feed the mock ws a `WSMessage(type=WSMsgType.TEXT, data="0{}", extra=None)` and confirm the consumer receives `(WSMsgType.TEXT, "0{}")`. (`WSMessage` is a NamedTuple in `aiohttp/_websocket/models.py` with fields `type: WSMsgType`, `data: Any`, `extra: Optional[str]`.)
  - **`receive()` raises `AbodeWebSocketError` on `WSMsgType.ERROR`**: the new module's exception type — see [Exception model](#exception-model).
  - **`receive()` stops on `WSMsgType.CLOSE` / `CLOSING` / `CLOSED`**: yields nothing further; the consumer must observe `closed == True` after. Implement this explicitly by updating the wrapper's closed state when a close-state frame ends iteration, rather than relying on a mock or aiohttp side effect.
  - **`close()` is idempotent**: calling it twice does not raise; the second call is a no-op.
  - **`close()` closes both the ws and the session**: assert both mocks' `close` were awaited.
  - **`closed` property**: starts `False`, becomes `True` after `close()`, and is `True` if `connect()` raised.
  - **Connect failures wrap as `AbodeWebSocketError`**: `aiohttp.ClientError` subclasses (e.g. `WSServerHandshakeError`, `ClientConnectorError`) raised from `ws_connect` come out as `AbodeWebSocketError` with the original as `__cause__`.
- [x] Run `uv run pytest tests/test_abode_websocket.py` — expect 11 failing tests, all with `ImportError: cannot import name 'AbodeWebSocket' from '...'._websocket`.

### Sub-Phase 2B: Implement the wrapper (TDD, GREEN)

- [x] Create `custom_components/abode_security/abode/_websocket.py` matching the contract in [Technical Details](#public-api).
- [x] Run `uv run pytest tests/test_abode_websocket.py -v` — all 11 tests pass.
- [x] Run `./scripts/check.sh` — typecheck, lint, full unit suite still clean.
- [x] Run `uv run pytest -m integration` — still green (no production callers were changed in this phase).

### Sub-Phase 2C: Confirm no production wiring leaked in

This sub-phase exists to catch the easy mistake of "while I'm here, let me just import it from `socketio.py`." It is in scope of Phase 3, not Phase 2.

- [x] Run `grep -rn "_websocket\|AbodeWebSocket" custom_components/ --include="*.py" | grep -v test_`. Only hits should be inside `_websocket.py` itself.
- [x] `manifest.json` requirements still contain `"lomond"`. (Phase 3 removes it.)

### Documentation (end of phase)

- [x] No `docs/` edits this phase. The wrapper is private (`_` prefix); architecture docs reference SocketIO behavior, which has not changed yet.
- [x] `UPSTREAM.md` — no change. Phase 3 updates the "Intentional rewrites" section once the rewrite is actually wired up.

### Build verification (required before marking phase complete)

- [x] `./scripts/check.sh` — clean.
- [x] `uv run pytest` — full unit suite green; count must equal Phase 1 baseline + 11 new tests for the wrapper.
- [x] `uv run pytest -m integration` — all 104 integration items green (unchanged from Phase 1 baseline).
- [x] Scan output for warnings; investigate any new ones.
- [x] Mark this file's frontmatter `status: done` only after every box above is checked.

### Manual verification with MCP tools (if available)

Skip — `_websocket.py` has no production callers yet. There is nothing user-visible to verify until Phase 3.

## Technical Details

### Public API

The wrapper is intentionally minimal — the SocketIO class already owns reconnect logic, backoff, ping handling, and framing. The wrapper handles only the WebSocket lifecycle.

```python
"""Async WebSocket wrapper over aiohttp.ClientWebSocketResponse."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import aiohttp

log = logging.getLogger(__name__)


class AbodeWebSocketError(Exception):
    """Transport-layer error from the AbodeWebSocket wrapper."""


class AbodeWebSocket:
    """Async wrapper around aiohttp.ClientWebSocketResponse.

    One AbodeWebSocket owns one aiohttp.ClientSession and one
    ClientWebSocketResponse. Reuse across reconnects: instantiate per
    connect cycle, await close(), discard.
    """

    def __init__(
        self,
        url: str,
        *,
        cookie: str | None = None,
        origin: str | None = None,
    ) -> None: ...

    @property
    def closed(self) -> bool: ...

    async def connect(self) -> None:
        """Open the WebSocket. Raises AbodeWebSocketError on failure."""

    async def send_text(self, data: str) -> None:
        """Send a text frame. Raises AbodeWebSocketError if not connected."""

    async def receive(self) -> AsyncIterator[tuple[aiohttp.WSMsgType, str]]:
        """Async iterator over incoming frames.

        Yields (type, text) tuples for TEXT messages. Stops iteration on
        WSMsgType.CLOSE / CLOSING / CLOSED and marks the wrapper closed.
        Raises AbodeWebSocketError on WSMsgType.ERROR. Ignores
        PING/PONG/BINARY frames (aiohttp handles autoping; PING/PONG never
        surface unless the caller disables it).
        """

    async def close(self) -> None:
        """Close the WebSocket and underlying session. Idempotent."""
```

### Exception model

`AbodeWebSocketError` is the wrapper's single exception type. Everything that goes wrong at the transport layer (handshake failure, connection drop, send-after-close, malformed frame type) raises `AbodeWebSocketError`. The original `aiohttp` exception is attached as `__cause__` via `raise ... from exc`.

This intentionally does **not** map onto `socketio.py`'s `SocketIOException` — that one belongs to the EngineIO/SocketIO framing layer above. Phase 3 will translate `AbodeWebSocketError` into `SocketIOException` at the boundary.

### Headers and `origin`

`aiohttp.ClientSession.ws_connect(url, headers=..., origin=...)` accepts a mapping for `headers` and a dedicated string kwarg `origin`. `Origin` MUST go through `origin=`; `Cookie` MUST go through `headers=` because there is no dedicated WebSocket cookie keyword.

Construct conditionally:

```python
headers: dict[str, str] | None = None
if self._cookie is not None:
    headers = {"Cookie": self._cookie}

await self._session.ws_connect(
    self._url,
    headers=headers,        # None when no cookie — aiohttp's default
    origin=self._origin,    # None when not set — aiohttp's default
    # Phase 3 callers may add heartbeat/timeout later; default for now.
)
```

This keeps the request shape identical to `lomond`'s no-extra-header default when both inputs are `None`. Passing an empty `{}` works but is noisier in test assertions and surfaces in network captures as an explicit content-less header dict, which `lomond` never produced.

### Receive: the wrapper iterates websocket messages; direct `ws.receive()` returns one message

`aiohttp.ClientWebSocketResponse.receive()` returns a **single** `WSMessage` per awaited call. The wrapper should expose an async-generator-style `receive()` API for SocketIO consumers, and it may implement that by iterating the websocket object itself. Sample shape:

```python
async def receive(self) -> AsyncIterator[tuple[aiohttp.WSMsgType, str]]:
    if self._ws is None:
        raise AbodeWebSocketError("receive() called before connect()")
    try:
        async for msg in self._ws:                    # ClientWebSocketResponse supports __aiter__
            if msg.type is aiohttp.WSMsgType.TEXT:
                yield (msg.type, msg.data)            # msg.data is str for TEXT
            elif msg.type is aiohttp.WSMsgType.ERROR:
                exc = self._ws.exception()
                raise AbodeWebSocketError("WebSocket ERROR frame") from exc
            elif msg.type in (
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.CLOSING,
                aiohttp.WSMsgType.CLOSED,
            ):
                self._closed = True                   # update wrapper state per the checklist contract
                return                                # graceful end of iteration
            # PING/PONG/BINARY: aiohttp handles autoping itself; ignore.
    except aiohttp.ClientError as exc:
        self._closed = True
        raise AbodeWebSocketError(str(exc)) from exc
```

`ClientWebSocketResponse` supports `async for msg in ws` directly, so the wrapper does NOT need a `while True: msg = await ws.receive()` polling loop. The `async for` exits cleanly on close frames.

### Test mocking: how to feed multiple frames to the wrapper

Because the wrapper iterates the underlying ws via `async for`, the test mock must implement async iteration. The simplest pattern:

```python
@pytest.fixture
def mock_ws():
    ws = AsyncMock(spec=aiohttp.ClientWebSocketResponse)
    ws.closed = False
    # Configure async iteration: return a list of WSMessage objects.
    ws.__aiter__.return_value = iter([
        aiohttp.WSMessage(type=aiohttp.WSMsgType.TEXT, data="0{}", extra=None),
        aiohttp.WSMessage(type=aiohttp.WSMsgType.CLOSED, data=None, extra=None),
    ])
    return ws
```

Note: `AsyncMock(spec=ClientWebSocketResponse)` does NOT automatically make `__aiter__` work the way `async for` expects — you may need a custom helper class or `MagicMock` for the iterator return value. If the test framework rejects either, fall back to a custom `class _FakeWS` that implements `__aiter__` / `__anext__` explicitly. The point of the test is the wrapper's framing logic, not aiohttp's iteration plumbing.

### Session ownership

The wrapper creates its own `aiohttp.ClientSession()` in `connect()` rather than receiving one from the caller. Reasoning: the existing `client.py` session has a tuned `TCPConnector(limit=10, limit_per_host=5)` and `ClientTimeout(total=30, connect=10, sock_read=10)` aimed at HTTP — those do not apply to a long-lived WebSocket. A separate session keeps the WS pool and the HTTP pool independent.

Phase 3 will pass an HA-supplied session in if and only if that proves necessary for cookie propagation; today's `socketio.py` propagates cookies via the `Cookie` header explicitly, so the separate-session approach is the default.

### Test mocking shape

Use `unittest.mock.AsyncMock` for the `aiohttp.ClientSession` and the `aiohttp.ClientWebSocketResponse`. Patch `aiohttp.ClientSession` at the wrapper-module level (`custom_components.abode_security.abode._websocket.aiohttp.ClientSession`) so the wrapper sees the mock when it calls the constructor.

Do not use `aioresponses` — that library mocks HTTP requests, not WebSocket handshakes.

Example test scaffold:

```python
import aiohttp
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.abode_security.abode._websocket import (
    AbodeWebSocket,
    AbodeWebSocketError,
)


@pytest.fixture
def mock_ws():
    ws = AsyncMock(spec=aiohttp.ClientWebSocketResponse)
    ws.closed = False
    return ws


@pytest.fixture
def mock_session(mock_ws):
    session = AsyncMock(spec=aiohttp.ClientSession)
    session.ws_connect = AsyncMock(return_value=mock_ws)
    return session


@pytest.fixture(autouse=True)
def patch_session(mock_session):
    with patch(
        "custom_components.abode_security.abode._websocket.aiohttp.ClientSession",
        return_value=mock_session,
    ):
        yield


@pytest.mark.asyncio
async def test_connect_passes_cookie_and_origin(mock_session):
    ws = AbodeWebSocket("wss://example/socket", cookie="sid=abc", origin="https://example")
    await ws.connect()
    mock_session.ws_connect.assert_awaited_once()
    call_kwargs = mock_session.ws_connect.await_args.kwargs
    # Cookie goes into headers (no dedicated kwarg); Origin uses aiohttp's
    # dedicated origin= keyword (do NOT also put it in headers).
    assert call_kwargs["headers"] == {"Cookie": "sid=abc"}
    assert call_kwargs["origin"] == "https://example"
```

## Constraints

- **No production callers in this phase.** If the `_websocket` import shows up outside the module itself and the test file, you're in Phase 3 territory — stop and revise.
- **Match the file convention.** Underscore prefix for internal modules; matches `_itertools.py`, `_ancestry.py`, `_collections.py`.
- **Keep the API minimal.** The SocketIO class above this wrapper owns reconnect, backoff, ping handling, and framing. Do not duplicate any of that here.
- **Do not introduce new runtime dependencies.** `aiohttp` is already in `manifest.json` requirements. No `websockets`, no `python-socketio`.
- **`AbodeWebSocketError` is the only exception this layer raises.** Wrap aiohttp exceptions with `raise AbodeWebSocketError(...) from exc`. Phase 3 owns the mapping to `SocketIOException`.
