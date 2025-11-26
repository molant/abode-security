"""Tests for Abode client error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from abode.client import Client
from abode.exceptions import RateLimitException
from abode.helpers import urls


class TestErrorHandling:
    """Test suite for error handling in abode client."""

    @pytest.mark.asyncio
    async def test_rate_limit_exception_with_retry_after(self) -> None:
        """Test RateLimitException is raised with Retry-After header."""
        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create mock response with 429 status and Retry-After header
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json = AsyncMock(return_value={
            "message": "Too many requests. Please try again later."
        })

        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"

        # send_request should raise RateLimitException
        with pytest.raises(RateLimitException) as exc_info:
            await client.send_request("get", urls.PANEL)

        # Verify retry_after was parsed
        assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_send_request_with_raise_on_error_false_returns_none_response(self) -> None:
        """Test send_request with raise_on_error=False returns response object."""
        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create mock response with error status
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="Not Found")

        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"

        # send_request should return response, not raise
        response = await client.send_request("get", urls.PANEL, raise_on_error=False)

        # Verify response is not None and has status
        assert response is not None
        assert response.status == 404
        assert response.body == "Not Found"

    @pytest.mark.asyncio
    async def test_get_test_mode_with_404_response(self) -> None:
        """Test get_test_mode handles 404 response gracefully."""
        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create mock response with 404
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="Not Found")

        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"
        client._panel = {}

        # get_test_mode should handle 404 and return False (disabled support)
        result = await client.get_test_mode()

        # Should return False when endpoint unavailable
        assert result is False
        assert client._test_mode_supported is False

    @pytest.mark.asyncio
    async def test_get_test_mode_with_valid_security_panel_response(self) -> None:
        """Test get_test_mode parses SECURITY_PANEL response correctly."""
        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create mock response with test mode data
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={
            "attributes": {
                "cms": {
                    "testModeActive": True
                }
            }
        })

        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"
        client._panel = {}

        # get_test_mode should return True
        result = await client.get_test_mode()

        # Should return True when testModeActive is true
        assert result is True

    @pytest.mark.asyncio
    async def test_get_test_mode_prefers_cached_panel_data(self) -> None:
        """Test get_test_mode prefers cached panel data over making API call."""
        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create client with cached panel data
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"
        client._panel = {
            "attributes": {
                "cms": {
                    "testModeActive": False
                }
            }
        }

        # get_test_mode should use cached data and not call API
        result = await client.get_test_mode()

        # Should return False from cached data
        assert result is False
        # Verify no API call was made
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_request_client_error_with_raise_on_error_false(self) -> None:
        """Test send_request handles ClientError with raise_on_error=False."""
        import aiohttp

        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Raise ClientError
        mock_get.side_effect = aiohttp.ClientError("Connection failed")

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"

        # send_request should return error response, not raise
        response = await client.send_request("get", urls.PANEL, raise_on_error=False)

        # Verify response is not None and contains error info
        assert response is not None
        assert response.status == 0
        assert "Connection failed" in response.body

    @pytest.mark.asyncio
    async def test_automations_endpoint_404_handled_gracefully(self) -> None:
        """Test get_automations handles 404 endpoint gracefully."""
        # Create a mock session
        mock_session = MagicMock()
        mock_get = AsyncMock()
        mock_session.get = mock_get

        # Create mock response with 404
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.headers = {}
        mock_response.text = AsyncMock(return_value="Not Found")

        mock_get.return_value.__aenter__.return_value = mock_response
        mock_get.return_value.__aexit__.return_value = None

        # Create client
        client = Client("test@example.com", "password", False, False, False)
        client._session = mock_session
        client._token = "test_token"
        client._oauth_token = "oauth_token"

        # get_automations should handle 404 and treat as zero automations
        await client.get_automations()

        # Should have empty automations
        assert client._automations == {}
