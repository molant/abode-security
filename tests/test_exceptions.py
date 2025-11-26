"""Tests for Abode exception classes."""

from http import HTTPStatus

import pytest
from abode.exceptions import (
    Exception as AbodeException,
    RateLimitException,
    SocketIOException,
)


class TestAbodeException:
    """Test suite for base Abode Exception."""

    def test_exception_initialization_with_tuple(self) -> None:
        """Test Exception initializes with (code, message) tuple."""
        error_tuple = (HTTPStatus.BAD_REQUEST, "Invalid credentials")
        exc = AbodeException(error_tuple)

        assert exc.errcode == HTTPStatus.BAD_REQUEST
        assert exc.message == "Invalid credentials"
        assert exc.args == error_tuple

    def test_exception_properties(self) -> None:
        """Test Exception properties return correct values."""
        error_tuple = (HTTPStatus.UNAUTHORIZED, "Authentication failed")
        exc = AbodeException(error_tuple)

        assert exc.errcode == HTTPStatus.UNAUTHORIZED
        assert exc.message == "Authentication failed"

    def test_exception_with_status_code_integers(self) -> None:
        """Test Exception works with integer status codes."""
        error_tuple = (401, "Unauthorized access")
        exc = AbodeException(error_tuple)

        assert exc.errcode == 401
        assert exc.message == "Unauthorized access"


class TestRateLimitException:
    """Test suite for RateLimitException."""

    def test_rate_limit_exception_initialization_with_retry_after(self) -> None:
        """Test RateLimitException initializes with retry_after."""
        error_tuple = (HTTPStatus.TOO_MANY_REQUESTS, "Too many requests")
        exc = RateLimitException(error_tuple, retry_after=60)

        assert exc.errcode == HTTPStatus.TOO_MANY_REQUESTS
        assert exc.message == "Too many requests"
        assert exc.retry_after == 60

    def test_rate_limit_exception_without_retry_after(self) -> None:
        """Test RateLimitException initializes without retry_after."""
        error_tuple = (429, "Rate limited")
        exc = RateLimitException(error_tuple)

        assert exc.errcode == 429
        assert exc.message == "Rate limited"
        assert exc.retry_after is None

    def test_rate_limit_exception_inherits_from_authentication_exception(self) -> None:
        """Test RateLimitException is an AuthenticationException."""
        from abode.exceptions import AuthenticationException

        error_tuple = (429, "Too many requests")
        exc = RateLimitException(error_tuple)

        assert isinstance(exc, AuthenticationException)
        assert isinstance(exc, AbodeException)

    def test_rate_limit_exception_with_zero_retry_after(self) -> None:
        """Test RateLimitException handles zero retry_after."""
        error_tuple = (429, "Rate limited")
        exc = RateLimitException(error_tuple, retry_after=0)

        assert exc.retry_after == 0


class TestSocketIOException:
    """Test suite for SocketIOException."""

    def test_socketio_exception_initialization(self) -> None:
        """Test SocketIOException initializes correctly."""
        error_tuple = (500, "Socket error")
        details = {"code": "SOCKET_ERROR", "message": "Connection failed"}

        exc = SocketIOException(error_tuple, details)

        assert exc.errcode == 500
        assert exc.message == "Socket error"
        assert exc.details == details

    def test_socketio_exception_with_empty_details(self) -> None:
        """Test SocketIOException can initialize with empty details."""
        error_tuple = (500, "Socket error")
        details = {}

        exc = SocketIOException(error_tuple, details)

        assert exc.errcode == 500
        assert exc.message == "Socket error"
        assert exc.details == {}

    def test_socketio_exception_inherits_from_abode_exception(self) -> None:
        """Test SocketIOException inherits from AbodeException."""
        error_tuple = (500, "Socket error")
        exc = SocketIOException(error_tuple, {})

        assert isinstance(exc, AbodeException)

    def test_socketio_exception_initialization_with_tuple_format(self) -> None:
        """Test SocketIOException properly calls parent __init__ with tuple."""
        error_tuple = (503, "Service unavailable")
        details = {"error": "Socket timeout"}

        # This should not raise TypeError: Exception.__init__() takes 2 positional arguments but 3 were given
        exc = SocketIOException(error_tuple, details)

        # Verify the exception was initialized properly
        assert exc.errcode == 503
        assert exc.message == "Service unavailable"
        # Verify details are stored
        assert exc.details == details

    def test_socketio_exception_string_representation(self) -> None:
        """Test SocketIOException string representation."""
        error_tuple = (500, "Internal server error")
        exc = SocketIOException(error_tuple, {"code": "INTERNAL_ERROR"})

        # Should be representable as string without errors
        str_repr = str(exc)
        assert "500" in str_repr or "Internal server error" in str_repr
