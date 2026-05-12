"""SocketIO inbound packet dispatch.

Regression: after the lomond-removal rewrite, `_on_engineio_message` resolved
`SocketIO.codes[0]` to `"connect"` and tried `getattr(self, "_on_socketio_connect")`,
but only `_on_socketio_connected` existed. Every successful namespace join
triggered an `AttributeError` that killed the receive task and made every HA
entity go unavailable. These tests feed raw Socket.IO v4 packets directly
through `_on_websocket_text` so that mismatch surfaces in CI.
"""

from custom_components.abode_security.abode.socketio import SocketIO


class TestInboundPacketDispatch:
    """Raw Engine.IO/Socket.IO packets must route to existing handlers."""

    async def test_connect_packet_sets_socketio_connected(self):
        """Packet '40' = EngineIO message (4) + SocketIO connect (0).

        The server sends this on every successful namespace join. If the
        method/dispatch-table names diverge again, this raises AttributeError
        and the test fails — mirroring the production crash.
        """
        s = SocketIO(url="ws://example/socket.io/")

        await s._on_websocket_text("40")

        assert s._socketio_connected is True

    async def test_disconnect_packet_clears_socketio_connected(self):
        """Packet '41' = EngineIO message (4) + SocketIO disconnect (1)."""
        s = SocketIO(url="ws://example/socket.io/")
        s._socketio_connected = True

        await s._on_websocket_text("41")

        assert s._socketio_connected is False

    async def test_every_socketio_code_has_a_handler(self):
        """Belt-and-braces: each entry in SocketIO.codes must resolve to a
        callable on the instance. Catches future drift between the dispatch
        table and the method names without needing one test per code."""
        s = SocketIO(url="ws://example/socket.io/")

        for name in SocketIO.codes:
            handler = getattr(s, f"_on_socketio_{name}", None)
            assert callable(handler), (
                f"SocketIO.codes has '{name}' but no _on_socketio_{name} method; "
                "the message dispatcher will AttributeError on this packet."
            )
