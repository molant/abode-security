"""Support for Abode Security System sensors."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, LIGHT_LUX, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .abode.devices.sensor import Sensor
from .const import DOMAIN
from .entity import AbodeDevice
from .models import AbodeSystem

PARALLEL_UPDATES = 1

ABODE_TEMPERATURE_UNIT_HA_UNIT = {
    "°F": UnitOfTemperature.FAHRENHEIT,
    "°C": UnitOfTemperature.CELSIUS,
}


@dataclass(frozen=True, kw_only=True)
class AbodeSensorDescription(SensorEntityDescription):
    """Class describing Abode sensor entities."""

    value_fn: Callable[[Sensor], float]
    native_unit_of_measurement_fn: Callable[[Sensor], str]


SENSOR_TYPES: tuple[AbodeSensorDescription, ...] = (
    AbodeSensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement_fn=lambda device: ABODE_TEMPERATURE_UNIT_HA_UNIT[
            device.temp_unit
        ],
        value_fn=lambda device: cast(float, device.temp),
    ),
    AbodeSensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement_fn=lambda _: PERCENTAGE,
        value_fn=lambda device: cast(float, device.humidity),
    ),
    AbodeSensorDescription(
        key="lux",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement_fn=lambda _: LIGHT_LUX,
        value_fn=lambda device: cast(float, device.lux),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Abode sensor devices."""
    from homeassistant.helpers import entity_registry as er

    data: AbodeSystem = entry.runtime_data

    devices = await data.abode.get_devices(generic_type="sensor")
    entities: list[SensorEntity] = []

    # Only add connection status sensor if it doesn't already exist
    entity_registry = er.async_get(hass)
    base_unique_id = data.abode.uuid or entry.data.get(CONF_USERNAME) or "abode"
    connection_unique_id = f"{base_unique_id}-connection-status"

    # Migrate legacy unique IDs (older versions used alarm ID or username)
    legacy_unique_ids: list[str] = []
    with contextlib.suppress(Exception):
        alarm = data.abode.get_alarm()
        if alarm:
            legacy_unique_ids.append(f"{alarm.id}-connection-status")
    if entry.data.get(CONF_USERNAME):
        legacy_unique_ids.append(f"{entry.data[CONF_USERNAME]}-connection-status")

    # Collapse any duplicate connection sensors by unique_id heuristic
    all_connection_entities = [
        entity
        for entity in entity_registry.entities.values()
        if entity.config_entry_id == entry.entry_id
        and entity.platform == DOMAIN
        and (
            entity.unique_id.endswith("connection-status")
            or "connection_status" in entity.entity_id
        )
    ]

    connection_sensor_exists = False

    # Attempt migration of legacy unique IDs
    if not connection_sensor_exists:
        for legacy_uid in legacy_unique_ids:
            if legacy_uid == connection_unique_id:
                continue
            if entity_id := entity_registry.async_get_entity_id(
                "sensor", DOMAIN, legacy_uid
            ):
                entity_registry.async_update_entity(
                    entity_id, new_unique_id=connection_unique_id
                )
                connection_sensor_exists = True
                break

    # Remove any extra duplicate entities beyond the canonical one
    for entity in all_connection_entities:
        if entity.unique_id != connection_unique_id:
            entity_registry.async_remove(entity.entity_id)

    if not connection_sensor_exists:
        entities.append(AbodeConnectionStatusSensor(data, connection_unique_id))

    for description in SENSOR_TYPES:
        for device in devices:
            if description.key in device.get_value("statuses"):
                entities.append(AbodeSensor(data, device, description))

    async_add_entities(entities)


class AbodeSensor(AbodeDevice, SensorEntity):
    """A sensor implementation for Abode devices."""

    entity_description: AbodeSensorDescription
    _device: Sensor

    def __init__(
        self,
        data: AbodeSystem,
        device: Sensor,
        description: AbodeSensorDescription,
    ) -> None:
        """Initialize a sensor for an Abode device."""
        super().__init__(data, device)
        self.entity_description = description
        self._attr_unique_id = f"{device.uuid}-{description.key}"

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self._device)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the native unit of measurement."""
        return self.entity_description.native_unit_of_measurement_fn(self._device)


class AbodeConnectionStatusSensor(SensorEntity):
    """Sensor reporting Abode connection status."""

    _attr_icon = "mdi:lan-connect"
    _attr_should_poll = True
    _unique_id: str

    def __init__(self, data: AbodeSystem, unique_id: str) -> None:
        """Initialize the connection status sensor."""
        self._data = data
        self._unique_id = unique_id
        self._attr_unique_id = unique_id
        self._attr_name = "Abode Connection Status"
        self._attr_native_value = data.abode.connection_status
        self._attr_extra_state_attributes: dict[str, str] = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "abode_system")},
            name="Abode System",
            manufacturer="Abode",
        )

    async def async_update(self) -> None:
        """Update connection status."""
        self._attr_native_value = self._data.abode.connection_status
        if (last_error := self._data.abode.last_error) is not None:
            self._attr_extra_state_attributes = {"last_error": last_error}
        else:
            self._attr_extra_state_attributes = {}
