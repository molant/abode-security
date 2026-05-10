"""Tests for the debug-log redaction helper in ``abode/client.py``.

Covers issue #49: tokens and other secrets must not appear in DEBUG logs that
users routinely paste into GitHub/community forums.
"""

import json
import logging

import pytest

from custom_components.abode_security.abode import client as client_module

SECRET_TOKEN = "live-session-token-aaaaaaaaaaaaaaaaaa"
SECRET_ACCESS = "live-access-token-bbbbbbbbbbbbbbbbbbbbbbbb"
SECRET_REFRESH = "live-refresh-cccccccccccccccccccccccc"
SECRET_PASSWORD = "hunter2-supersecret"


def _flatten(value):
    """Render any value into a single string for substring assertions."""
    if isinstance(value, dict | list):
        return json.dumps(value)
    return str(value)


class TestRedact:
    """Unit tests for ``client._redact``."""

    def test_login_response_redacts_token_and_user_pii(self) -> None:
        payload = {
            "token": SECRET_TOKEN,
            "panel": {"mac": "AA:BB:CC:DD:EE:FF"},
            "user": {
                "email": "victim@example.com",
                "phone": "+15551234567",
                "uuid": "11111111-2222-3333-4444-555555555555",
            },
        }

        redacted = client_module._redact(payload)

        assert redacted["token"] == "<redacted>"
        assert redacted["user"]["email"] == "<redacted>"
        assert redacted["user"]["phone"] == "<redacted>"
        assert redacted["user"]["uuid"] == "<redacted>"
        # Non-secret fields are preserved.
        assert redacted["panel"]["mac"] == "AA:BB:CC:DD:EE:FF"
        # The secret string itself must not survive anywhere in the structure.
        assert SECRET_TOKEN not in _flatten(redacted)

    def test_oauth_nested_dict_is_redacted(self) -> None:
        payload = {
            "outer": {
                "access_token": SECRET_ACCESS,
                "refresh_token": SECRET_REFRESH,
                "id_token": "id.jwt.value",
                "expires_in": 3600,
            }
        }

        redacted = client_module._redact(payload)

        assert redacted["outer"]["access_token"] == "<redacted>"
        assert redacted["outer"]["refresh_token"] == "<redacted>"
        assert redacted["outer"]["id_token"] == "<redacted>"
        assert redacted["outer"]["expires_in"] == 3600
        assert SECRET_ACCESS not in _flatten(redacted)
        assert SECRET_REFRESH not in _flatten(redacted)

    def test_redact_is_case_insensitive(self) -> None:
        payload = {"Token": SECRET_TOKEN, "Set-Cookie": "session=abc"}

        redacted = client_module._redact(payload)

        assert redacted["Token"] == "<redacted>"
        assert redacted["Set-Cookie"] == "<redacted>"

    def test_redact_walks_lists(self) -> None:
        payload = [
            {"token": SECRET_TOKEN, "name": "Front Door"},
            {"password": SECRET_PASSWORD, "name": "Back Door"},
        ]

        redacted = client_module._redact(payload)

        assert redacted[0]["token"] == "<redacted>"
        assert redacted[0]["name"] == "Front Door"
        assert redacted[1]["password"] == "<redacted>"
        assert SECRET_TOKEN not in _flatten(redacted)
        assert SECRET_PASSWORD not in _flatten(redacted)

    def test_redact_passes_through_primitives(self) -> None:
        assert client_module._redact("hello") == "hello"
        assert client_module._redact(42) == 42
        assert client_module._redact(None) is None
        assert client_module._redact(True) is True

    def test_redact_does_not_mutate_input(self) -> None:
        payload = {"token": SECRET_TOKEN, "nested": {"access_token": SECRET_ACCESS}}
        original = json.loads(json.dumps(payload))

        client_module._redact(payload)

        assert payload == original


class TestRedactText:
    """``_redact_text`` parses JSON-shaped strings, redacts, and re-serializes."""

    def test_redact_text_handles_json_payload(self) -> None:
        raw = json.dumps({"token": SECRET_TOKEN, "status": "ok"})

        result = client_module._redact_text(raw)

        assert "<redacted>" in result
        assert SECRET_TOKEN not in result
        assert "ok" in result

    def test_redact_text_returns_summary_for_non_json(self) -> None:
        raw = "not-json-but-might-contain-token=" + SECRET_TOKEN

        result = client_module._redact_text(raw)

        assert SECRET_TOKEN not in result
        # Should communicate something about the body without leaking it.
        assert "len=" in result or "non-json" in result.lower()


class TestDebugLogsAreClean:
    """Capture debug logs at the integration points and grep for secrets."""

    def _set_token_and_session(self, client):
        """Bypass ``__init__`` defaults for tests that don't need a real session."""
        client._session = object()
        client._token = "preexisting"

    @pytest.mark.asyncio
    async def test_login_debug_log_redacts_token(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Simulate the login log line and assert the token is redacted."""
        # We don't drive the real ``login()`` (it needs HTTP); we replay the
        # specific ``log.debug`` call that ``login()`` makes after parsing the
        # response, which is the exact line called out in the issue.
        response_object = {
            "token": SECRET_TOKEN,
            "panel": {"mac": "AA:BB:CC:DD:EE:FF"},
            "user": {"email": "victim@example.com"},
        }

        with caplog.at_level(logging.DEBUG, logger=client_module.log.name):
            client_module.log.debug(
                "Login Response: %s", client_module._redact(response_object)
            )

        rendered = "\n".join(record.getMessage() for record in caplog.records)
        assert SECRET_TOKEN not in rendered
        assert "victim@example.com" not in rendered
        assert "<redacted>" in rendered
