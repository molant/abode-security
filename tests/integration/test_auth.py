"""Integration tests for authentication using mock server."""

import os

import pytest
from abode_security.abode.client import Client as Abode


@pytest.mark.integration
async def test_login_with_mock_server(mock_server_client):
    """Test successful login using mock server."""
    # Set base URL for this test
    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    try:
        abode = Abode(
            username=mock_server_client["username"],
            password=mock_server_client["password"],
            auto_login=False,
        )

        # Test login
        await abode.login()

        # Verify token was set
        assert abode.token is not None
        assert abode.user_id is not None

        # Cleanup
        await abode.logout()
    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_login_invalid_credentials(mock_server_client):
    """Test login with invalid credentials returns error."""
    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    try:
        abode = Abode(
            username="wrong@example.com",
            password="wrongpassword",
            auto_login=False,
        )

        # Should raise exception
        with pytest.raises(Exception):  # Adjust exception type based on client
            await abode.login()
    finally:
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_auto_login_with_mock_server(abode_with_mock_server):
    """Test auto_login parameter with mock server."""
    abode = abode_with_mock_server

    # Should already be logged in due to auto_login=True
    assert abode.token is not None
    assert abode.user_id is not None


@pytest.mark.integration
async def test_get_panel_after_login(abode_with_mock_server):
    """Test fetching panel data after successful login."""
    abode = abode_with_mock_server

    # Get panel data
    panel = await abode.get_panel()

    # Verify panel data structure
    assert panel is not None
    assert "mode" in panel
    assert "area_1" in panel["mode"]
