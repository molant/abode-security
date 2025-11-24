"""Async wrapper for jaraco.abode library operations.

Provides async-compatible methods for synchronous jaraco.abode operations.
This eliminates the need for executor jobs for blocking I/O operations.
"""

from __future__ import annotations

from typing import Any, TypeVar

from homeassistant.core import HomeAssistant

from .const import LOGGER

T = TypeVar("T")


async def async_call(
    hass: HomeAssistant,
    func: callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Call a synchronous function asynchronously using executor.

    This is a utility function that wraps blocking operations in an executor
    to prevent blocking the event loop.

    Args:
        hass: Home Assistant instance
        func: Synchronous function to call
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value from func
    """
    return await hass.async_add_executor_job(func, *args, **kwargs)


async def async_get_alarm(
    hass: HomeAssistant,
    abode_client: Any,
) -> Any:
    """Get alarm state asynchronously.

    Args:
        hass: Home Assistant instance
        abode_client: Abode client instance

    Returns:
        Alarm device object
    """
    LOGGER.debug("Fetching alarm state asynchronously")
    return await async_call(hass, abode_client.get_alarm)


async def async_get_devices(
    hass: HomeAssistant,
    abode_client: Any,
    generic_type: str | None = None,
) -> list[Any]:
    """Get devices asynchronously.

    Args:
        hass: Home Assistant instance
        abode_client: Abode client instance
        generic_type: Optional device type filter

    Returns:
        List of device objects
    """
    LOGGER.debug("Fetching devices asynchronously (type: %s)", generic_type)
    if generic_type:
        return await async_call(hass, abode_client.get_devices, generic_type=generic_type)
    return await async_call(hass, abode_client.get_devices)


async def async_get_automations(
    hass: HomeAssistant,
    abode_client: Any,
) -> list[Any]:
    """Get automations asynchronously.

    Args:
        hass: Home Assistant instance
        abode_client: Abode client instance

    Returns:
        List of automation objects
    """
    LOGGER.debug("Fetching automations asynchronously")
    return await async_call(hass, abode_client.get_automations)


async def async_set_standby(
    hass: HomeAssistant,
    alarm: Any,
) -> None:
    """Set alarm to standby (disarmed) asynchronously.

    Args:
        hass: Home Assistant instance
        alarm: Alarm device object
    """
    LOGGER.debug("Setting alarm to standby asynchronously")
    await async_call(hass, alarm.set_standby)


async def async_set_home(
    hass: HomeAssistant,
    alarm: Any,
) -> None:
    """Set alarm to home (armed home) asynchronously.

    Args:
        hass: Home Assistant instance
        alarm: Alarm device object
    """
    LOGGER.debug("Setting alarm to home mode asynchronously")
    await async_call(hass, alarm.set_home)


async def async_set_away(
    hass: HomeAssistant,
    alarm: Any,
) -> None:
    """Set alarm to away (armed away) asynchronously.

    Args:
        hass: Home Assistant instance
        alarm: Alarm device object
    """
    LOGGER.debug("Setting alarm to away mode asynchronously")
    await async_call(hass, alarm.set_away)


async def async_add_event_callback(
    hass: HomeAssistant,
    events: Any,
    event_group: str,
    callback: callable,
) -> None:
    """Add event callback asynchronously.

    Args:
        hass: Home Assistant instance
        events: Events manager object
        event_group: Event group to subscribe to
        callback: Callback function for events
    """
    LOGGER.debug("Adding event callback asynchronously for %s", event_group)
    await async_call(hass, events.add_event_callback, event_group, callback)


async def async_remove_event_callback(
    hass: HomeAssistant,
    events: Any,
    event_group: str,
    callback: callable,
) -> None:
    """Remove event callback asynchronously.

    Args:
        hass: Home Assistant instance
        events: Events manager object
        event_group: Event group to unsubscribe from
        callback: Callback function to remove
    """
    LOGGER.debug("Removing event callback asynchronously for %s", event_group)
    await async_call(hass, events.remove_event_callback, event_group, callback)


# Batch Operations


async def async_batch_device_operations(
    hass: HomeAssistant,
    operations: list[tuple[str, Any, str]],
) -> list[Any]:
    """Execute multiple device operations in a batch.

    Groups multiple operations together to reduce API calls.

    Args:
        hass: Home Assistant instance
        operations: List of (operation_type, device, action) tuples
                   operation_type: 'switch_on', 'switch_off', 'lock', 'unlock', etc.
                   device: Device object
                   action: Optional action parameter

    Returns:
        List of results from each operation
    """
    LOGGER.debug("Executing batch device operations (%d ops)", len(operations))
    results = []

    for op_type, device, action in operations:
        try:
            if op_type == "switch_on":
                result = await async_call(hass, device.switch_on)
            elif op_type == "switch_off":
                result = await async_call(hass, device.switch_off)
            elif op_type == "lock":
                result = await async_call(hass, device.lock)
            elif op_type == "unlock":
                result = await async_call(hass, device.unlock)
            elif op_type == "close_cover":
                result = await async_call(hass, device.close_cover)
            elif op_type == "open_cover":
                result = await async_call(hass, device.open_cover)
            else:
                LOGGER.warning("Unknown batch operation: %s", op_type)
                result = None

            results.append(result)
            LOGGER.debug("Batch operation %s completed successfully", op_type)

        except Exception as ex:
            LOGGER.error("Batch operation %s failed: %s", op_type, ex)
            results.append(None)

    return results


async def async_batch_read_devices(
    hass: HomeAssistant,
    devices: list[Any],
) -> list[dict[str, Any]]:
    """Read status from multiple devices in batch.

    Efficiently fetch status from multiple devices.

    Args:
        hass: Home Assistant instance
        devices: List of device objects

    Returns:
        List of device status dictionaries
    """
    LOGGER.debug("Reading batch device status (%d devices)", len(devices))
    results = []

    for device in devices:
        try:
            status = {
                "id": device.device_id,
                "name": device.name,
                "type": device.type,
                "status": device.status,
                "battery": getattr(device, "battery", None),
            }
            results.append(status)
        except Exception as ex:
            LOGGER.error("Failed to read device status for %s: %s", device.name, ex)
            results.append({"id": getattr(device, "device_id", None), "error": str(ex)})

    return results
