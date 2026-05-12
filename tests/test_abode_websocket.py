"""Unit tests for abode/_websocket.py.

These tests cover the public surface of AbodeWebSocket:
 - Construction does not open a connection
 - connect() issues ws_connect with correct headers/origin
 - connect() omits headers when no cookie, passes origin=None when no origin
 - send_text() delegates to underlying ws.send_str
 - receive() yields TEXT frames as (WSMsgType.TEXT, str)
 - receive() raises AbodeWebSocketError on WSMsgType.ERROR
 - receive() stops on CLOSE/CLOSING/CLOSED and marks closed
 - close() is idempotent
 - close() closes both ws and session
 - closed property starts False, becomes True after close() or failed connect()
 - connect() failures wrap aiohttp.ClientError as AbodeWebSocketError
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.abode_security.abode._websocket import (
    AbodeWebSocket,
    AbodeWebSocketError,
)


def _make_mock_ws(frames: list[aiohttp.WSMessage]) -> MagicMock:
    """Return a mock ClientWebSocketResponse that iterates over *frames*."""

    class _FakeAsyncIter:
        def __init__(self, items):
            self._iter = iter(items)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

    ws = AsyncMock(spec=aiohttp.ClientWebSocketResponse)
    ws.closed = False
    ws.__aiter__ = lambda _: _FakeAsyncIter(frames)
    return ws


@pytest.fixture
def mock_ws():
    return _make_mock_ws([])


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


# ---------------------------------------------------------------------------
# Test 1: Construction does not open a connection
# ---------------------------------------------------------------------------


def test_construction_does_not_connect(mock_session):
    AbodeWebSocket("wss://example/socket", cookie="sid=abc", origin="https://example")
    mock_session.ws_connect.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2: connect() round-trip — correct headers and origin kwarg
# ---------------------------------------------------------------------------


async def test_connect_passes_cookie_and_origin(mock_session):
    ws = AbodeWebSocket(
        "wss://example/socket", cookie="sid=abc", origin="https://example"
    )
    await ws.connect()
    mock_session.ws_connect.assert_awaited_once()
    call_kwargs = mock_session.ws_connect.await_args.kwargs
    # Cookie goes into headers (no dedicated kwarg); Origin uses aiohttp's
    # dedicated origin= keyword (do NOT also put it in headers).
    assert call_kwargs["headers"] == {"Cookie": "sid=abc"}
    assert call_kwargs["origin"] == "https://example"


# ---------------------------------------------------------------------------
# Test 3: connect() omits Cookie header when no cookie; origin=None when absent
# ---------------------------------------------------------------------------


async def test_connect_no_cookie_no_origin(mock_session):
    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    mock_session.ws_connect.assert_awaited_once()
    call_kwargs = mock_session.ws_connect.await_args.kwargs
    assert call_kwargs.get("headers") is None
    assert call_kwargs.get("origin") is None


# ---------------------------------------------------------------------------
# Test 4: send_text() delegates to ws.send_str
# ---------------------------------------------------------------------------


async def test_send_text_delegates(mock_ws):
    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    await ws.send_text("hello world")
    mock_ws.send_str.assert_awaited_once_with("hello world")


async def test_send_text_raises_before_connect():
    ws = AbodeWebSocket("wss://example/socket")
    with pytest.raises(AbodeWebSocketError):
        await ws.send_text("should fail")


async def test_send_text_raises_after_close():
    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    await ws.close()
    with pytest.raises(AbodeWebSocketError):
        await ws.send_text("should fail")


async def test_receive_raises_before_connect():
    ws = AbodeWebSocket("wss://example/socket")
    with pytest.raises(AbodeWebSocketError):
        async for _ in ws.receive():
            pass


async def test_receive_raises_after_close():
    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    await ws.close()
    with pytest.raises(AbodeWebSocketError):
        async for _ in ws.receive():
            pass


# ---------------------------------------------------------------------------
# Test 5: receive() yields TEXT frames as (WSMsgType.TEXT, str)
# ---------------------------------------------------------------------------


async def test_receive_yields_text_frames(mock_session):
    frames = [
        aiohttp.WSMessage(type=aiohttp.WSMsgType.TEXT, data="0{}", extra=None),
    ]
    ws_mock = _make_mock_ws(frames)
    mock_session.ws_connect = AsyncMock(return_value=ws_mock)

    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    received = [frame async for frame in ws.receive()]
    assert received == [(aiohttp.WSMsgType.TEXT, "0{}")]


# ---------------------------------------------------------------------------
# Test 6: receive() raises AbodeWebSocketError on WSMsgType.ERROR
# ---------------------------------------------------------------------------


async def test_receive_raises_on_error_frame(mock_session):
    frames = [
        aiohttp.WSMessage(type=aiohttp.WSMsgType.ERROR, data=None, extra=None),
    ]
    ws_mock = _make_mock_ws(frames)
    ws_mock.exception.return_value = None
    mock_session.ws_connect = AsyncMock(return_value=ws_mock)

    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    with pytest.raises(AbodeWebSocketError):
        async for _ in ws.receive():
            pass


# ---------------------------------------------------------------------------
# Test 7: receive() stops on CLOSE/CLOSING/CLOSED and marks wrapper closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "close_type",
    [
        aiohttp.WSMsgType.CLOSE,
        aiohttp.WSMsgType.CLOSING,
        aiohttp.WSMsgType.CLOSED,
    ],
)
async def test_receive_stops_on_close(mock_session, close_type):
    frames = [
        aiohttp.WSMessage(type=aiohttp.WSMsgType.TEXT, data="first", extra=None),
        aiohttp.WSMessage(type=close_type, data=None, extra=None),
        aiohttp.WSMessage(type=aiohttp.WSMsgType.TEXT, data="never", extra=None),
    ]
    ws_mock = _make_mock_ws(frames)
    mock_session.ws_connect = AsyncMock(return_value=ws_mock)

    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    received = [frame async for frame in ws.receive()]
    assert received == [(aiohttp.WSMsgType.TEXT, "first")]
    assert ws.closed is True


async def test_close_after_receive_close_frame_still_cleans_up(mock_session):
    """close() must clean up ws+session even if receive() already set _closed."""
    frames = [
        aiohttp.WSMessage(type=aiohttp.WSMsgType.CLOSE, data=None, extra=None),
    ]
    ws_mock = _make_mock_ws(frames)
    mock_session.ws_connect = AsyncMock(return_value=ws_mock)

    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    [_ async for _ in ws.receive()]  # exhausts the generator; sets _closed=True
    assert ws.closed is True
    await ws.close()  # should still close ws and session
    ws_mock.close.assert_awaited_once()
    mock_session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 8: close() is idempotent — calling twice does not raise
# ---------------------------------------------------------------------------


async def test_close_is_idempotent():
    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    await ws.close()
    await ws.close()  # must not raise


# ---------------------------------------------------------------------------
# Test 9: close() closes both the ws and the session
# ---------------------------------------------------------------------------


async def test_close_closes_ws_and_session(mock_session, mock_ws):
    ws = AbodeWebSocket("wss://example/socket")
    await ws.connect()
    await ws.close()
    mock_ws.close.assert_awaited_once()
    mock_session.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 10: closed property lifecycle
# ---------------------------------------------------------------------------


async def test_closed_property_lifecycle():
    ws = AbodeWebSocket("wss://example/socket")
    assert ws.closed is False
    await ws.connect()
    assert ws.closed is False
    await ws.close()
    assert ws.closed is True


async def test_closed_true_when_connect_raises(mock_session):
    mock_session.ws_connect = AsyncMock(
        side_effect=aiohttp.ClientConnectorError(
            connection_key=MagicMock(), os_error=OSError("refused")
        )
    )
    ws = AbodeWebSocket("wss://example/socket")
    assert ws.closed is False
    with pytest.raises(AbodeWebSocketError):
        await ws.connect()
    assert ws.closed is True


# ---------------------------------------------------------------------------
# Test 11: connect() wraps aiohttp.ClientError as AbodeWebSocketError
# ---------------------------------------------------------------------------


async def test_connect_wraps_client_error(mock_session):
    original = aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError("connection refused")
    )
    mock_session.ws_connect = AsyncMock(side_effect=original)

    ws = AbodeWebSocket("wss://example/socket")
    with pytest.raises(AbodeWebSocketError) as exc_info:
        await ws.connect()
    assert exc_info.value.__cause__ is original
