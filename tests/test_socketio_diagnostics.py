"""Tests for SocketIO health counter properties (Sub-Phase 4A)."""

from __future__ import annotations

import datetime

from custom_components.abode_security.abode.socketio import SocketIO

URL = "ws://example.com/socket.io/"


class TestSocketIODiagnosticProperties:
    """SocketIO exposes read-only health counters for diagnostics."""

    def _make_sio(self) -> SocketIO:
        return SocketIO(URL)

    def test_consecutive_connect_failures_initial_zero(self) -> None:
        sio = self._make_sio()
        assert sio.consecutive_connect_failures == 0

    def test_last_packet_age_seconds_none_before_first_packet(self) -> None:
        sio = self._make_sio()
        assert sio.last_packet_age_seconds is None

    def test_last_packet_age_seconds_reflects_elapsed_time(self) -> None:
        sio = self._make_sio()
        sio._last_packet_time = datetime.datetime.now(
            tz=datetime.UTC
        ) - datetime.timedelta(seconds=42)
        age = sio.last_packet_age_seconds
        assert age is not None
        assert 40 <= age <= 45
