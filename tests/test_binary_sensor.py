"""Tests for the Abode Security binary sensor device."""

import logging
import os
from unittest.mock import MagicMock

import pytest
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_STATE_CHANGED,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_component import DATA_INSTANCES
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abode_security import ATTR_DEVICE_ID
from custom_components.abode_security.abode.devices.binary_sensor import (
    BinarySensor,
    Connectivity,
    Motion,
)
from custom_components.abode_security.binary_sensor import AbodeBinarySensor
from custom_components.abode_security.const import ATTRIBUTION, CONF_POLLING, DOMAIN

from .common import setup_platform

# The platform module's logger, so the transition-log test asserts against the
# same logger production writes to.
_BINARY_SENSOR_LOGGER = "custom_components.abode_security.binary_sensor"


async def test_entity_registry(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    aiohttp_mock,  # noqa: ARG001
) -> None:
    """Tests that the devices are registered in the entity registry.

    Uses `aiohttp_mock` so the real `Client` can run through login/devices
    fetch against canned fixtures (`tests/fixtures/devices.json`) — the
    `front_door` sensor and its unique_id come from that fixture.
    """
    await setup_platform(hass, BINARY_SENSOR_DOMAIN)

    entry = entity_registry.async_get("binary_sensor.front_door")
    assert entry is not None
    assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"


@pytest.mark.integration
async def test_binary_sensor_attributes(
    hass: HomeAssistant, mock_server_client: dict[str, str]
) -> None:
    """Test the binary sensor attributes are correct."""
    # Set environment variable to point to mock server
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    # Reload urls module to pick up the new environment variable
    importlib.reload(urls)

    try:
        # Create config entry with mock server credentials
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)

        # Set up the integration - this will make real HTTP calls to mock server
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify entity attributes
        state = hass.states.get("binary_sensor.front_door")
        assert state is not None
        assert state.state == STATE_OFF
        assert state.attributes.get(ATTR_ATTRIBUTION) == ATTRIBUTION
        assert state.attributes.get(ATTR_DEVICE_ID) == "RF:01430030"
        assert not state.attributes.get("battery_low")
        assert not state.attributes.get("no_response")
        assert state.attributes.get("device_type") == "Door Contact"
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Front Door"
        assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.WINDOW

    finally:
        # Restore original environment
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


@pytest.mark.integration
async def test_binary_sensor_with_mock_server(
    hass: HomeAssistant,
    mock_server_client: dict[str, str],
    entity_registry: er.EntityRegistry,
) -> None:
    """Test binary sensor entity creation using mock server."""
    # Set environment variable to point to mock server
    import importlib

    from custom_components.abode_security.abode.helpers import urls

    original_url = os.environ.get("ABODE_BASE_URL")
    os.environ["ABODE_BASE_URL"] = mock_server_client["base_url"]

    # Reload urls module to pick up the new environment variable
    importlib.reload(urls)

    try:
        # Create config entry with mock server credentials
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_USERNAME: mock_server_client["username"],
                CONF_PASSWORD: mock_server_client["password"],
                CONF_POLLING: False,
            },
        )
        config_entry.add_to_hass(hass)

        # Set up the integration - this will make real HTTP calls to mock server
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify entity was created in registry
        entry = entity_registry.async_get("binary_sensor.front_door")
        assert entry is not None
        assert entry.unique_id == "2834013428b6035fba7d4054aa7b25a3"

        # Verify entity state and attributes
        state = hass.states.get("binary_sensor.front_door")
        assert state is not None
        assert state.state == STATE_OFF
        assert state.attributes.get(ATTR_ATTRIBUTION) == ATTRIBUTION
        assert state.attributes.get(ATTR_DEVICE_ID) == "RF:01430030"
        assert state.attributes.get("device_type") == "Door Contact"
        assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Front Door"
        assert state.attributes.get(ATTR_DEVICE_CLASS) == BinarySensorDeviceClass.WINDOW

    finally:
        # Restore original environment
        if original_url is not None:
            os.environ["ABODE_BASE_URL"] = original_url
        elif "ABODE_BASE_URL" in os.environ:
            del os.environ["ABODE_BASE_URL"]


# --- Regression tests for status → state mapping (issue #210) ---


def _make_binary_sensor(
    cls: type[BinarySensor],
    status: str | None,
    *,
    device_type: str = "Door Contact",
    no_response: int = 0,
    tag: str | None = None,
) -> BinarySensor:
    """Build a bare vendored device with just the state `is_on` reads."""
    state: dict[str, object] = {
        "id": "RF:0000dead",
        "uuid": "0000dead",
        "type": device_type,
        "name": "Test Sensor",
        "faults": {"no_response": no_response},
    }
    # `resolve_class` never runs (the class is instantiated directly), but
    # `Connectivity.is_reporting` keys off the tag, and keeping it consistent
    # stops the fixture describing a device shape it isn't. `BinarySensor`
    # itself declares no tags.
    if tag or cls.tags:
        state["type_tag"] = f"device_type.{tag or cls.tags[0]}"
    if status is not None:
        state["status"] = status
    return cls(state, None)


def _make_entity(device: BinarySensor) -> AbodeBinarySensor:
    """Build a binary sensor entity around a vendored device."""
    data = MagicMock()
    data.polling = False
    data.abode.events.connected = True
    return AbodeBinarySensor(data, device)


@pytest.mark.parametrize(
    ("status", "expected_is_on", "expected_is_reporting"),
    [
        ("Closed", False, True),
        ("Open", True, True),
        ("Off", False, True),
        ("On", True, True),
        # An offline sensor keeps its last known status, so it must not read as
        # "clear" — that is what turned an offline blip on an open window into a
        # spurious "off" -> "on" activation.
        ("Offline", False, False),
        # A device doc without a status field is not evidence of anything.
        (None, False, False),
        ("", False, False),
    ],
)
def test_binary_sensor_status_mapping(
    status: str | None, expected_is_on: bool, expected_is_reporting: bool
) -> None:
    """Status maps to `is_on`/`is_reporting` without conflating the two."""
    device = _make_binary_sensor(BinarySensor, status)

    assert device.is_on is expected_is_on
    assert device.is_reporting is expected_is_reporting


def test_binary_sensor_no_response_fault_is_not_reporting() -> None:
    """A `no_response` fault means the status is stale even when it looks fine."""
    device = _make_binary_sensor(BinarySensor, "Open", no_response=1)

    assert device.is_reporting is False
    # The last known status is still surfaced; availability is what changes.
    assert device.is_on is True


@pytest.mark.parametrize(
    ("status", "expected_is_on", "expected_is_reporting"),
    [
        ("Online", False, True),
        # `status not in STATUS.ONLINE` was a substring test: every substring of
        # "Online" read as clear and "Offline" read as occupied.
        ("On", True, True),
        ("Offline", False, False),
        ("", False, False),
        (None, False, False),
    ],
)
def test_occupancy_status_mapping(
    status: str | None, expected_is_on: bool, expected_is_reporting: bool
) -> None:
    """Occupancy compares against the status, not its characters."""
    device = _make_binary_sensor(Motion, status, device_type="Occupancy")

    assert device.is_on is expected_is_on
    assert device.is_reporting is expected_is_reporting


def test_motion_non_occupancy_uses_base_mapping() -> None:
    """A plain motion sensor keeps the shared `BinarySensor` mapping.

    `Online` reading as `is_on` is upstream behaviour preserved deliberately,
    not a mapping this test claims is correct: motion for these devices
    arrives over the timeline rather than through device status. Out of scope
    for #210 — pinned here only so a change to it is a visible edit.
    """
    device = _make_binary_sensor(Motion, "Online", device_type="Motion Camera")

    assert device.is_on is True


@pytest.mark.parametrize("tag", ["glass", "keypad", "remote_controller", "siren", "bx"])
@pytest.mark.parametrize(
    ("status", "expected_is_on"),
    [("Online", True), ("Offline", False)],
)
def test_link_state_tags_report_offline_as_a_state(
    tag: str, status: str, expected_is_on: bool
) -> None:
    """For link-state tags `Offline` is the reading, not a stale status.

    These render with the `connectivity` device class, where `off` means
    "Disconnected" — the one state they exist to report. Withholding it as
    `unavailable` (as contacts and motion sensors now do) would erase it.
    """
    device = _make_binary_sensor(Connectivity, status, device_type="Keypad", tag=tag)

    assert device.is_reporting is True
    assert device.is_on is expected_is_on


def test_link_state_tag_reports_through_a_no_response_fault() -> None:
    """The tag exemption wins over the fault: `off` still means Disconnected."""
    device = _make_binary_sensor(
        Connectivity, "Offline", device_type="Keypad", tag="keypad", no_response=1
    )

    assert device.is_reporting is True
    assert device.is_on is False


def test_link_state_entity_stays_available_when_offline() -> None:
    """The entity for an offline keypad reports `off`, not gone."""
    entity = _make_entity(
        _make_binary_sensor(Connectivity, "Offline", device_type="Keypad", tag="keypad")
    )

    assert entity.available is True
    assert entity.is_on is False


@pytest.mark.parametrize(
    ("tag", "device_type"),
    [
        ("water_sensor", "Water Sensor"),
        ("smoke_detector", "Smoke Detector"),
        ("fix_panic", "Panic Button"),
    ],
)
def test_payload_tags_in_connectivity_still_treat_offline_as_stale(
    tag: str, device_type: str
) -> None:
    """`Connectivity` is overloaded; its payload-carrying tags get the fix.

    A water sensor reports `On`/`Off` for moisture, so an offline blip must not
    read as "dry" — these are exactly the sensors a user wires an action to,
    and the trigger coordinator does not filter by device class.
    """
    device = _make_binary_sensor(
        Connectivity, "Offline", device_type=device_type, tag=tag
    )

    assert device.is_reporting is False


def test_motion_pir_offline_is_stale() -> None:
    """A PIR that dropped off the network withholds its status like a contact."""
    device = _make_binary_sensor(
        Motion, "Offline", device_type="Motion Camera", tag="pir"
    )

    assert device.is_reporting is False


def test_entity_unavailable_when_device_offline() -> None:
    """An offline device reports `unavailable`, not `off` (issue #210)."""
    entity = _make_entity(_make_binary_sensor(BinarySensor, "Offline"))

    assert entity.available is False


def test_entity_available_when_device_reporting() -> None:
    """A reporting device stays available and mirrors its status."""
    entity = _make_entity(_make_binary_sensor(BinarySensor, "Open"))

    assert entity.available is True
    assert entity.is_on is True


def test_entity_availability_tracks_device_updates() -> None:
    """Going offline and back flips availability, never `on` -> `off` -> `on`."""
    device = _make_binary_sensor(BinarySensor, "Open")
    entity = _make_entity(device)
    assert entity.available is True
    assert entity.is_on is True

    device.update({"status": "Offline"})
    entity._sync_attrs()  # noqa: SLF001 — stands in for the device callback
    assert entity.available is False

    device.update({"status": "Open"})
    entity._sync_attrs()  # noqa: SLF001
    assert entity.available is True
    assert entity.is_on is True


def test_socketio_reconnect_does_not_clobber_device_availability() -> None:
    """The SocketIO callback must not mark an offline device available again."""
    entity = _make_entity(_make_binary_sensor(BinarySensor, "Offline"))
    entity.schedule_update_ha_state = MagicMock()  # type: ignore[method-assign]

    entity._update_connection_status()  # noqa: SLF001

    assert entity.available is False


def test_reporting_transitions_are_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The measurement log fires on transitions only — not on every sync.

    This line is the instrument for judging whether unavailable-on-offline is
    noisier than the false trigger it removes, so silence on the first sync
    and on repeated syncs at the same reporting state is the point.
    """
    device = _make_binary_sensor(BinarySensor, "Open")

    with caplog.at_level(logging.INFO, logger=_BINARY_SENSOR_LOGGER):
        entity = _make_entity(device)
        assert caplog.records == []  # first sync establishes a baseline only

        entity._sync_attrs()  # noqa: SLF001
        assert caplog.records == []  # unchanged reporting state stays quiet

        device.update({"status": "Offline"})
        entity._sync_attrs()  # noqa: SLF001
        assert len(caplog.records) == 1
        assert "stopped reporting" in caplog.records[0].getMessage()

        entity._sync_attrs()  # noqa: SLF001
        assert len(caplog.records) == 1  # still offline, still quiet

        device.update({"status": "Open"})
        entity._sync_attrs()  # noqa: SLF001
        assert len(caplog.records) == 2
        assert "resumed reporting" in caplog.records[1].getMessage()


def test_connection_loss_marks_reporting_device_unavailable() -> None:
    """Losing SocketIO still marks a healthy device unavailable."""
    entity = _make_entity(_make_binary_sensor(BinarySensor, "Open"))
    entity.schedule_update_ha_state = MagicMock()  # type: ignore[method-assign]
    entity._data.abode.events.connected = False  # noqa: SLF001

    entity._update_connection_status()  # noqa: SLF001

    assert entity.available is False


def _get_platform_entity(hass: HomeAssistant, entity_id: str) -> AbodeBinarySensor:
    """Fetch a live platform entity so its device state can be driven."""
    component = hass.data[DATA_INSTANCES][BINARY_SENSOR_DOMAIN]
    return next(
        entity  # type: ignore[misc]
        for entity in component.entities
        if entity.entity_id == entity_id
    )


async def test_offline_blip_never_looks_like_a_fresh_activation(
    hass: HomeAssistant,
    aiohttp_mock,  # noqa: ARG001
) -> None:
    """End-to-end guard for #210, through the real HA state machine.

    The earlier unit tests assert on `entity.available`; this one asserts on
    what `ActionTriggerCoordinator._handle_state_change` actually reads — the
    states HA writes. An open window whose contact drops off the RF network
    must go `on` -> `unavailable` -> `on`, never `on` -> `off` -> `on`, since
    only the latter is the `off` -> `on` transition that fires an action.
    """
    await setup_platform(hass, BINARY_SENSOR_DOMAIN)

    entity = _get_platform_entity(hass, "binary_sensor.front_door")
    observed: list[str] = []

    def _record(event: Event) -> None:
        if event.data["entity_id"] == "binary_sensor.front_door":
            observed.append(event.data["new_state"].state)

    hass.bus.async_listen(EVENT_STATE_CHANGED, _record)

    async def _push_status(status: str) -> None:
        entity._device.update({"status": status})  # noqa: SLF001
        entity._update_callback(entity._device)  # noqa: SLF001
        await hass.async_block_till_done()

    await _push_status("Open")
    await _push_status("Offline")
    await _push_status("Open")

    assert observed == [STATE_ON, STATE_UNAVAILABLE, STATE_ON]
    # The discriminator: before the fix the offline blip wrote "off" here, and
    # the return to "Open" was then an off -> on activation.
    assert STATE_OFF not in observed
