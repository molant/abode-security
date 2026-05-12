"""Async WebSocket wrapper over aiohttp.ClientWebSocketResponse."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import aiohttp

log = logging.getLogger(__name__)


class AbodeWebSocketError(Exception):
    """Transport-layer error from the AbodeWebSocket wrapper."""


class AbodeWebSocket:
    """Async wrapper around aiohttp.ClientWebSocketResponse.

    Instantiate once per connect cycle; do not reuse across reconnects.
    await close() when done, then discard.
    """

    def __init__(
        self,
        url: str,
        *,
        cookie: str | None = None,
        origin: str | None = None,
    ) -> None:
        self._url = url
        self._cookie = cookie
        self._origin = origin
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._closed = False
        self._cleanup_done = False  # tracks whether ws+session were actually closed

    @property
    def closed(self) -> bool:
        return self._closed

    async def connect(self) -> None:
        """Open the WebSocket. Raises AbodeWebSocketError on failure."""
        headers: dict[str, str] | None = None
        if self._cookie is not None:
            headers = {"Cookie": self._cookie}

        self._session = aiohttp.ClientSession()
        try:
            self._ws = await self._session.ws_connect(
                self._url,
                headers=headers,
                origin=self._origin,
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            self._closed = True
            await self._session.close()
            self._cleanup_done = True
            raise AbodeWebSocketError(str(exc)) from exc

    async def send_text(self, data: str) -> None:
        """Send a text frame. Raises AbodeWebSocketError if not connected."""
        if self._closed or self._ws is None:
            raise AbodeWebSocketError("send_text() called on closed connection")
        await self._ws.send_str(data)

    async def receive(self) -> AsyncIterator[tuple[aiohttp.WSMsgType, str]]:
        """Async generator over incoming frames.

        Yields (type, text) tuples for TEXT messages. Stops iteration on
        WSMsgType.CLOSE / CLOSING / CLOSED and marks the wrapper closed.
        Raises AbodeWebSocketError on WSMsgType.ERROR. Ignores
        PING/PONG/BINARY frames.

        Note: this is an async generator. The pre-connection guard raises on
        the *first iteration*, not when receive() is called.
        """
        if self._closed or self._ws is None:
            raise AbodeWebSocketError("receive() called on closed or unconnected socket")
        try:
            async for msg in self._ws:
                if msg.type is aiohttp.WSMsgType.TEXT:
                    yield (msg.type, msg.data)
                elif msg.type is aiohttp.WSMsgType.ERROR:
                    self._closed = True
                    exc = self._ws.exception()
                    raise AbodeWebSocketError("WebSocket ERROR frame") from exc
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSING,
                    aiohttp.WSMsgType.CLOSED,
                ):
                    self._closed = True
                    return
        except aiohttp.ClientError as exc:
            self._closed = True
            raise AbodeWebSocketError(str(exc)) from exc

    async def close(self) -> None:
        """Close the WebSocket and underlying session. Idempotent."""
        self._closed = True
        if self._cleanup_done:
            return
        self._cleanup_done = True
        try:
            if self._ws is not None:
                await self._ws.close()
        finally:
            if self._session is not None:
                await self._session.close()
