"""Decorators for common operations."""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

from .const import LOGGER
from .exceptions import AbodeException

_T = TypeVar("_T")


def handle_abode_errors(operation_name: str) -> Callable:
    """Decorator to handle Abode API exceptions consistently.

    Args:
        operation_name: Human-readable operation description for logging

    Returns:
        Decorated function that catches AbodeException and logs errors
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except AbodeException as ex:
                LOGGER.error(f"Failed to {operation_name}: %s", ex)
                return None

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except AbodeException as ex:
                LOGGER.error(f"Failed to {operation_name}: %s", ex)
                return None

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
