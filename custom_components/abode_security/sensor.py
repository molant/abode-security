"""Support for Abode Security System sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from abode.devices.sensor import Sensor
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import _vendor  # noqa: F401
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
    connection_sensor_exists = any(
        entity.config_entry_id == entry.entry_id
        and entity.platform == "abode_security"
        and "connection_status" in entity.entity_id
        for entity in entity_registry.entities.values()
    )

    if not connection_sensor_exists:
        entities.append(AbodeConnectionStatusSensor(data))

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

    def __init__(self, data: AbodeSystem) -> None:
        """Initialize the connection status sensor."""
        self._data = data
        self._attr_unique_id = f"{data.abode.uuid}-connection-status"
        self._attr_name = "Abode Connection Status"
        self._attr_native_value = data.abode.connection_status
        self._attr_extra_state_attributes = {}

    async def async_update(self) -> None:
        """Update connection status."""
        self._attr_native_value = self._data.abode.connection_status
        if (last_error := self._data.abode.last_error) is not None:
            self._attr_extra_state_attributes = {"last_error": last_error}
        else:
            self._attr_extra_state_attributes = {}
