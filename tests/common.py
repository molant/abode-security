"""Common methods used across tests for Abode Security."""

from pathlib import Path
from unittest.mock import patch

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import DOMAIN
from custom_components.abode_security.const import CONF_POLLING


def load_fixture(filename: str, integration: str = "abode_security") -> str:  # noqa: ARG001
    """Load a fixture file."""
    fixtures_path = Path(__file__).resolve().parent / "fixtures"
    fixture_file = fixtures_path / filename
    return fixture_file.read_text(encoding="utf-8")


async def setup_platform(hass: HomeAssistant, platform: str) -> MockConfigEntry:
    """Set up the Abode Security platform."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "user@email.com",
            CONF_PASSWORD: "password",
            CONF_POLLING: False,
        },
    )
    mock_entry.add_to_hass(hass)

    with (
        patch("custom_components.abode_security.PLATFORMS", [platform]),
        patch("abode.event_controller.sio"),
    ):
        assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    return mock_entry
