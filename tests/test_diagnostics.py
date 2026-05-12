"""Tests for the diagnostics payload (issue #50).

The integration sets ``ConfigEntry.unique_id`` to the user's Abode username,
which is their email address. Diagnostics bundles are routinely attached to
support tickets and public forum threads, so any PII must be redacted before
it leaves the user's instance.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from custom_components.abode_security import diagnostics

EMAIL = "victim@example.com"


def _make_abode_system(*, socketio_inst: object = None) -> MagicMock:
    """Build a minimal AbodeSystem mock.

    Pass ``socketio_inst=<mock>`` to inject a SocketIO instance into the
    diagnostics walk (``events.socketio``).  The default ``None`` means no
    SocketIO instance is present — diagnostics should omit the ``"socketio"``
    key rather than raising.
    """
    abode_system = MagicMock()
    abode_system.polling = True
    abode_system.polling_interval = 30
    abode_system.enable_events = True
    abode_system.retry_count = 3
    abode_system.abode.get_devices = AsyncMock(return_value=[])
    abode_system.abode.get_automations = AsyncMock(return_value=[])
    abode_system.abode.get_alarm = MagicMock(
        return_value=MagicMock(type="alarm", battery="ok")
    )
    abode_system.abode.events.connected = True
    abode_system.abode.connection_diagnostics = {"status": "ok"}
    # Set the public EventController.socketio property so diagnostics can find it.
    abode_system.abode.events.socketio = socketio_inst
    return abode_system


def _run_diagnostics(abode_system: MagicMock | None = None) -> dict:
    """Build minimal mocks and call ``async_get_config_entry_diagnostics``."""
    if abode_system is None:
        abode_system = _make_abode_system()

    entry = MagicMock()
    entry.runtime_data = abode_system
    entry.unique_id = EMAIL

    return asyncio.run(
        diagnostics.async_get_config_entry_diagnostics(MagicMock(), entry)
    )


class TestDiagnosticsRedaction:
    """The diagnostics payload must not leak the user's email or other PII."""

    def test_unique_id_is_redacted(self) -> None:
        result = _run_diagnostics()

        assert result["unique_id"] == "**REDACTED**"

    def test_email_does_not_appear_anywhere_in_payload(self) -> None:
        result = _run_diagnostics()

        # JSON-serialize the whole payload and grep for the email — this is the
        # exact failure mode the issue describes (PII reaching a support ticket).
        assert EMAIL not in json.dumps(result, default=str)


class TestDiagnosticsSocketIOCounters:
    """SocketIO health counters surface correctly in the diagnostics payload."""

    def test_socketio_counters_present_when_socketio_available(self) -> None:
        socketio_mock = MagicMock()
        socketio_mock.consecutive_connect_failures = 3
        socketio_mock.last_packet_age_seconds = 4.2

        result = _run_diagnostics(_make_abode_system(socketio_inst=socketio_mock))

        assert result["socketio"] == {
            "consecutive_connect_failures": 3,
            "last_packet_age_seconds": 4.2,
        }

    def test_socketio_counters_absent_when_socketio_is_none(self) -> None:
        result = _run_diagnostics(_make_abode_system(socketio_inst=None))

        assert "socketio" not in result

    def test_diagnostics_succeeds_when_events_attr_missing(self) -> None:
        abode_system = _make_abode_system()
        # Remove the events attribute entirely so getattr falls back to None.
        del abode_system.abode.events

        result = _run_diagnostics(abode_system)

        assert "socketio" not in result
        assert "connection_status" in result
