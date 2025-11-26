"""Tests for Abode client URL construction."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from abode.helpers import urls

from custom_components.abode_security.const import DOMAIN


class TestURLConstruction:
    """Test suite for URL construction in abode client."""

    def test_base_url_no_double_slash(self) -> None:
        """Test that BASE URL doesn't end with a trailing slash.

        This prevents double slashes when concatenating with paths.
        Paths start with '/', so BASE should not end with '/'.
        """
        assert not urls.BASE.endswith("/"), f"BASE URL should not end with '/': {urls.BASE}"

    def test_base_url_correct_format(self) -> None:
        """Test BASE URL has correct format."""
        assert urls.BASE == "https://my.goabode.com", f"Unexpected BASE URL: {urls.BASE}"

    def test_endpoint_urls_no_leading_slash_duplication(self) -> None:
        """Test endpoint URL constants all start with single slash (not double)."""
        endpoints = [
            ("LOGIN", urls.LOGIN),
            ("LOGOUT", urls.LOGOUT),
            ("PANEL", urls.PANEL),
            ("DEVICES", urls.DEVICES),
            ("AUTOMATION", urls.AUTOMATION),
            ("CMS_SETTINGS", urls.CMS_SETTINGS),
            ("SECURITY_PANEL", urls.SECURITY_PANEL),
        ]

        for name, endpoint in endpoints:
            # Each endpoint should start with exactly one slash
            assert endpoint.startswith("/"), f"{name} should start with '/': {endpoint}"
            assert not endpoint.startswith("//"), f"{name} should not start with '//': {endpoint}"

    @pytest.mark.asyncio
    async def test_url_construction_in_send_request(self) -> None:
        """Test that send_request constructs URLs without double slashes."""
        from abode.client import Client
        from unittest.mock import MagicMock

        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"test": "data"})

        # Make the context manager work
        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"

        # Call send_request with a path
        await client.send_request("get", urls.PANEL)

        # Verify the URL called had no double slashes
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        url_called = call_args[0][0] if call_args[0] else call_args.kwargs.get("url")

        # The URL should not have double slashes after the protocol
        assert "https://my.goabode.com/api/v1/panel" == url_called, (
            f"URL should not have double slashes: {url_called}"
        )
        assert "//" not in url_called.replace("https://", ""), (
            f"URL contains double slashes (excluding protocol): {url_called}"
        )

    @pytest.mark.parametrize("endpoint,expected_path", [
        (urls.LOGIN, "https://my.goabode.com/api/auth2/login"),
        (urls.LOGOUT, "https://my.goabode.com/api/v1/logout"),
        (urls.PANEL, "https://my.goabode.com/api/v1/panel"),
        (urls.DEVICES, "https://my.goabode.com/api/v1/devices"),
        (urls.AUTOMATION, "https://my.goabode.com/integrations/v1/automations/"),
        (urls.CMS_SETTINGS, "https://my.goabode.com/integrations/v1/cms/settings"),
        (urls.SECURITY_PANEL, "https://my.goabode.com/integrations/v1/security-panel"),
    ])
    def test_combined_url_no_double_slash(self, endpoint: str, expected_path: str) -> None:
        """Test that combining BASE + endpoint produces correct URLs without double slashes."""
        combined_url = f"{urls.BASE}{endpoint}"
        assert combined_url == expected_path, (
            f"URL construction failed for {endpoint}: "
            f"expected {expected_path}, got {combined_url}"
        )
        # Verify no double slashes
        assert "//" not in combined_url.replace("https://", ""), (
            f"Combined URL has double slashes: {combined_url}"
        )
