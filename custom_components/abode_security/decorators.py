"""Decorators for common operations."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, TypeVar

from homeassistant.exceptions import HomeAssistantError

from .abode.exceptions import Exception as AbodeException
from .const import LOGGER

_T = TypeVar("_T")


def handle_abode_errors(operation_name: str) -> Callable:
    """Log Abode API failures with context, then re-raise for Home Assistant.

    This used to catch `.exceptions.AbodeError`, which nothing in the codebase
    ever raises — the embedded client raises `.abode.exceptions.Exception`. The
    decorator was therefore a no-op passthrough, and the comments claiming it
    "swallows" errors were wrong.

    It now catches the class actually raised, but deliberately **re-raises**
    rather than returning None. Every decorated method is a user- or
    automation-initiated command on a security system (arm, disarm, raise an
    alarm, change a CMS setting); silently degrading one to a no-op is how a
    failed action ends up looking like a successful one. Wrapping in
    `HomeAssistantError` gets the reason in front of the user instead of a bare
    stack trace, and keeps it visible to callers such as the actions executor,
    which records it in `alarms_failed`.

    Args:
        operation_name: Human-readable operation description for logging

    Returns:
        Decorated function that logs and re-raises Abode API errors.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except AbodeException as ex:
                LOGGER.error("Failed to %s: %s", operation_name, ex)
                raise HomeAssistantError(f"Failed to {operation_name}: {ex}") from ex

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except AbodeException as ex:
                LOGGER.error("Failed to %s: %s", operation_name, ex)
                raise HomeAssistantError(f"Failed to {operation_name}: {ex}") from ex

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return decorator
