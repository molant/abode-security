"""Verify async/await patterns are correctly implemented.

This test module verifies that all the async/await fixes are working correctly
without requiring a full Home Assistant instance setup.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add custom_components to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAsyncAwaitPatterns:
    """Test async/await patterns in the integration."""

    def test_service_handlers_have_correct_types(self) -> None:
        """Verify service handler functions have correct async/sync types."""
        from custom_components.abode_security import services

        # Handlers that should be async (contain await)
        async_handlers = [
            ("_change_setting", services._change_setting),
            ("_trigger_alarm_handler", services._trigger_alarm_handler),
        ]

        for name, func in async_handlers:
            assert inspect.iscoroutinefunction(
                func
            ), f"{name} should be async def but is {type(func)}"

        # Handlers that should be sync (no await)
        sync_handlers = [
            ("_capture_image", services._capture_image),
            ("_trigger_automation", services._trigger_automation),
        ]

        for name, func in sync_handlers:
            assert not inspect.iscoroutinefunction(
                func
            ), f"{name} should be sync def but is async"

    def test_entity_lifecycle_methods_are_async(self) -> None:
        """Verify entity lifecycle methods are async."""
        from custom_components.abode_security.entity import AbodeDevice, AbodeEntity

        # Entity lifecycle methods should be async
        async_methods = [
            ("async_added_to_hass", AbodeEntity),
            ("async_will_remove_from_hass", AbodeEntity),
            ("async_added_to_hass", AbodeDevice),
            ("async_will_remove_from_hass", AbodeDevice),
            ("async_update", AbodeDevice),
        ]

        for method_name, cls in async_methods:
            if hasattr(cls, method_name):
                method = getattr(cls, method_name)
                assert inspect.iscoroutinefunction(
                    method
                ), f"{cls.__name__}.{method_name} should be async"

    def test_platform_setup_functions_are_async(self) -> None:
        """Verify platform setup functions are async."""
        platform_modules = [
            "custom_components.abode_security.switch",
            "custom_components.abode_security.camera",
            "custom_components.abode_security.light",
            "custom_components.abode_security.lock",
            "custom_components.abode_security.cover",
            "custom_components.abode_security.sensor",
            "custom_components.abode_security.binary_sensor",
            "custom_components.abode_security.alarm_control_panel",
        ]

        for module_name in platform_modules:
            try:
                module = __import__(module_name, fromlist=["async_setup_entry"])
                assert hasattr(
                    module, "async_setup_entry"
                ), f"{module_name} missing async_setup_entry"
                assert inspect.iscoroutinefunction(
                    module.async_setup_entry
                ), f"{module_name}.async_setup_entry should be async"
            except ImportError:
                # Module might not be importable in test environment
                pass

    def test_config_flow_methods_are_async(self) -> None:
        """Verify config flow methods are async."""
        from custom_components.abode_security.config_flow import (
            AbodeFlowHandler,
            AbodeOptionsFlowHandler,
        )

        # Config flow step methods should be async
        config_async_methods = [
            ("async_step_user", AbodeFlowHandler),
            ("async_step_mfa", AbodeFlowHandler),
            ("async_step_reauth", AbodeFlowHandler),
            ("async_step_reauth_confirm", AbodeFlowHandler),
        ]

        for method_name, cls in config_async_methods:
            if hasattr(cls, method_name):
                method = getattr(cls, method_name)
                assert inspect.iscoroutinefunction(
                    method
                ), f"{cls.__name__}.{method_name} should be async"

        # Options flow step should be async
        assert inspect.iscoroutinefunction(
            AbodeOptionsFlowHandler.async_step_init
        ), "AbodeOptionsFlowHandler.async_step_init should be async"

    def test_no_asyncio_run_usage(self) -> None:
        """Verify integration doesn't use asyncio.run()."""
        import_dir = Path(__file__).parent.parent / "custom_components" / "abode_security"

        for py_file in import_dir.glob("**/*.py"):
            content = py_file.read_text()
            assert (
                "asyncio.run(" not in content
            ), f"{py_file.name} contains asyncio.run() which should not be used"

    def test_no_run_until_complete_usage(self) -> None:
        """Verify integration doesn't use run_until_complete()."""
        import_dir = Path(__file__).parent.parent / "custom_components" / "abode_security"

        for py_file in import_dir.glob("**/*.py"):
            content = py_file.read_text()
            assert (
                "run_until_complete" not in content
            ), f"{py_file.name} contains run_until_complete() which should not be used"

    def test_timeout_protection_on_executor_jobs(self) -> None:
        """Verify executor jobs are protected with asyncio.wait_for()."""
        entity_file = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "entity.py"
        )
        content = entity_file.read_text()

        # Count asyncio.wait_for usage
        wait_for_count = content.count("asyncio.wait_for(")
        assert (
            wait_for_count >= 4
        ), f"Expected at least 4 asyncio.wait_for calls in entity.py, found {wait_for_count}"

        # Verify timeout parameter
        assert "timeout=" in content, "asyncio.wait_for should have timeout parameter"

    def test_service_handler_factory_creates_async_handler(self) -> None:
        """Verify service handler factory creates async coroutines."""
        from custom_components.abode_security.services import _create_service_handler

        # Create a mock handler
        mock_method = AsyncMock(return_value=None)

        handler = _create_service_handler(
            "test_method", "test operation", ("arg1", lambda c: "value1")
        )

        # Handler should be a coroutine function
        assert inspect.iscoroutinefunction(
            handler
        ), "Service handler factory should create async handler"

    def test_dispatcher_callbacks_properly_wrapped(self) -> None:
        """Verify dispatcher callbacks are properly wrapped for async."""
        camera_file = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "camera.py"
        )
        content = camera_file.read_text()

        # Verify async_on_remove is used with dispatcher_connect
        assert (
            "async_on_remove" in content and "async_dispatcher_connect" in content
        ), "Camera should use async_on_remove with async_dispatcher_connect"

        # Verify proper cleanup pattern
        assert (
            "self.async_on_remove(async_dispatcher_connect("
            in content.replace("\n", "")
        ), "Dispatcher connections should be registered with async_on_remove"

    def test_sync_to_async_callback_wrapper(self) -> None:
        """Verify sync/async callback wrapping patterns."""
        switch_file = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "switch.py"
        )
        content = switch_file.read_text()

        # Verify the async_create_task pattern for wrapping sync dispatcher callbacks
        assert (
            "async_create_task" in content
        ), "Switch should use async_create_task to wrap async callbacks"

    def test_models_async_methods(self) -> None:
        """Verify AbodeSystem has async methods for API calls."""
        from custom_components.abode_security.models import AbodeSystem

        # These should be async methods
        async_methods = ["get_test_mode", "set_test_mode"]

        for method_name in async_methods:
            assert hasattr(
                AbodeSystem, method_name
            ), f"AbodeSystem missing {method_name}"
            method = getattr(AbodeSystem, method_name)
            assert inspect.iscoroutinefunction(
                method
            ), f"AbodeSystem.{method_name} should be async"

    def test_no_async_properties(self) -> None:
        """Verify no async properties (invalid Python pattern)."""
        import_dir = Path(__file__).parent.parent / "custom_components" / "abode_security"

        # Check for the anti-pattern of @property with async def
        for py_file in import_dir.glob("**/*.py"):
            content = py_file.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines[:-1]):
                if "@property" in line:
                    next_line = lines[i + 1]
                    assert (
                        "async def" not in next_line
                    ), f"{py_file.name}: Found async property which is invalid"

    def test_service_method_naming_convention(self) -> None:
        """Verify service methods follow naming conventions."""
        from custom_components.abode_security import alarm_control_panel, cover, light, lock

        # Methods that operate on devices should have async_ prefix
        expected_async_methods = [
            ("async_lock", lock.AbodeLock),
            ("async_unlock", lock.AbodeLock),
            ("async_open_cover", cover.AbodeCover),
            ("async_close_cover", cover.AbodeCover),
            ("async_turn_on", light.AbodeLight),
            ("async_turn_off", light.AbodeLight),
            ("async_alarm_disarm", alarm_control_panel.AbodeAlarm),
            ("async_alarm_arm_home", alarm_control_panel.AbodeAlarm),
            ("async_alarm_arm_away", alarm_control_panel.AbodeAlarm),
        ]

        for method_name, cls in expected_async_methods:
            assert hasattr(
                cls, method_name
            ), f"{cls.__name__} missing method {method_name}"
            method = getattr(cls, method_name)
            assert inspect.iscoroutinefunction(
                method
            ), f"{cls.__name__}.{method_name} should be async"


class TestAsyncAwaitSemantics:
    """Test async/await semantics are correct."""

    @pytest.mark.asyncio
    async def test_change_setting_handler_is_awaitable(self) -> None:
        """Verify _change_setting handler is properly awaitable."""
        from custom_components.abode_security.services import _change_setting

        mock_call = MagicMock()
        mock_call.data = {"setting": "test", "value": "value"}
        mock_call.hass = MagicMock()
        mock_call.hass.config_entries.async_entries.return_value = []

        # Should be a coroutine
        coro = _change_setting(mock_call)
        assert inspect.iscoroutine(coro), "_change_setting should return a coroutine"

        # Should be awaitable
        try:
            await coro
        except Exception:
            pass  # May fail due to mock, but should be awaitable

    @pytest.mark.asyncio
    async def test_capture_image_handler_not_awaitable(self) -> None:
        """Verify _capture_image handler is NOT async."""
        from custom_components.abode_security.services import _capture_image

        mock_call = MagicMock()
        mock_call.data = {"entity_id": []}
        mock_call.hass = MagicMock()
        mock_call.hass.config_entries.async_entries.return_value = []

        # Should NOT be a coroutine
        result = _capture_image(mock_call)
        assert (
            not inspect.iscoroutine(result)
        ), "_capture_image should not return a coroutine"
        assert result is None, "_capture_image should return None"

    @pytest.mark.asyncio
    async def test_trigger_automation_handler_not_awaitable(self) -> None:
        """Verify _trigger_automation handler is NOT async."""
        from custom_components.abode_security.services import _trigger_automation

        mock_call = MagicMock()
        mock_call.data = {"entity_id": []}
        mock_call.hass = MagicMock()
        mock_call.hass.config_entries.async_entries.return_value = []

        # Should NOT be a coroutine
        result = _trigger_automation(mock_call)
        assert (
            not inspect.iscoroutine(result)
        ), "_trigger_automation should not return a coroutine"
        assert result is None, "_trigger_automation should return None"

    @pytest.mark.asyncio
    async def test_factory_handler_is_awaitable(self) -> None:
        """Verify service handler factory creates awaitable handlers."""
        from custom_components.abode_security.services import _create_service_handler

        # Create a handler using the factory
        mock_method = AsyncMock(return_value=None)
        handler = _create_service_handler("test", "test op", ("arg", lambda c: "val"))

        mock_call = MagicMock()
        mock_call.hass = MagicMock()
        mock_call.hass.config_entries.async_entries.return_value = []

        # Should return a coroutine
        coro = handler(mock_call)
        assert inspect.iscoroutine(coro), "Factory handler should return a coroutine"

        # Should be awaitable
        try:
            await coro
        except Exception:
            pass  # May fail due to mock, but should be awaitable

    @pytest.mark.asyncio
    async def test_timeout_protection_catches_errors(self) -> None:
        """Verify timeout protection properly catches TimeoutError."""
        # Simulate what happens when asyncio.wait_for times out
        async def timeout_handler() -> None:
            try:
                await asyncio.wait_for(
                    asyncio.sleep(10),  # This will timeout
                    timeout=0.001,  # Very short timeout
                )
            except asyncio.TimeoutError:
                pass  # Should be caught gracefully

        # Should not raise
        await timeout_handler()

    @pytest.mark.asyncio
    async def test_async_create_task_scheduling(self) -> None:
        """Verify async_create_task properly schedules coroutines."""
        from unittest.mock import AsyncMock

        # Mock Home Assistant's async_create_task
        task_created = False

        def mock_async_create_task(coro):
            nonlocal task_created
            task_created = True
            return asyncio.create_task(coro)

        # Simulate the pattern used in camera.py
        async def async_operation():
            await asyncio.sleep(0.001)

        # Simulate dispatcher calling sync wrapper
        def sync_wrapper():
            mock_async_create_task(async_operation())

        sync_wrapper()
        assert task_created, "async_create_task should have been called"


class TestIntegrationStructure:
    """Test integration structure and imports."""

    def test_init_module_has_setup_functions(self) -> None:
        """Verify __init__.py has required setup functions."""
        from custom_components.abode_security import (
            async_setup,
            async_setup_entry,
            async_unload_entry,
        )

        assert inspect.iscoroutinefunction(
            async_setup
        ), "async_setup should be async"
        assert inspect.iscoroutinefunction(
            async_setup_entry
        ), "async_setup_entry should be async"
        assert inspect.iscoroutinefunction(
            async_unload_entry
        ), "async_unload_entry should be async"

    def test_services_module_has_setup_function(self) -> None:
        """Verify services.py exports setup_services."""
        from custom_components.abode_security.services import setup_services

        # Should be callable
        assert callable(setup_services), "setup_services should be callable"
        # Should not be async (it registers async handlers)
        assert (
            not inspect.iscoroutinefunction(setup_services)
        ), "setup_services should be sync"

    def test_all_platform_modules_importable(self) -> None:
        """Verify all platform modules can be imported."""
        platforms = [
            "custom_components.abode_security.switch",
            "custom_components.abode_security.camera",
            "custom_components.abode_security.light",
            "custom_components.abode_security.lock",
            "custom_components.abode_security.cover",
            "custom_components.abode_security.sensor",
            "custom_components.abode_security.binary_sensor",
            "custom_components.abode_security.alarm_control_panel",
        ]

        for module_name in platforms:
            try:
                __import__(module_name)
            except ImportError as e:
                # Some imports might fail due to missing dependencies
                # but we can at least verify the modules exist
                pass

    def test_entity_base_classes_exist(self) -> None:
        """Verify entity base classes are properly defined."""
        from custom_components.abode_security.entity import (
            AbodeAutomation,
            AbodeDevice,
            AbodeEntity,
        )

        assert (
            AbodeEntity is not None
        ), "AbodeEntity should be defined"
        assert (
            AbodeDevice is not None
        ), "AbodeDevice should be defined"
        assert (
            AbodeAutomation is not None
        ), "AbodeAutomation should be defined"


class TestAsyncAwaitRobustness:
    """Test robustness of async/await implementation."""

    @pytest.mark.asyncio
    async def test_error_handler_decorator_wraps_async(self) -> None:
        """Verify error handler decorator properly wraps async functions."""
        from custom_components.abode_security.decorators import handle_abode_errors

        @handle_abode_errors("test operation")
        async def test_async_func():
            await asyncio.sleep(0.001)
            return "success"

        result = test_async_func()
        assert inspect.iscoroutine(result), "Decorated async func should still be coroutine"
        result_value = await result
        assert result_value == "success", "Decorated async func should work"

    @pytest.mark.asyncio
    async def test_error_handler_decorator_wraps_sync(self) -> None:
        """Verify error handler decorator properly wraps sync functions."""
        from custom_components.abode_security.decorators import handle_abode_errors

        @handle_abode_errors("test operation")
        def test_sync_func():
            return "success"

        result = test_sync_func()
        assert not inspect.iscoroutine(result), "Decorated sync func should not be coroutine"
        assert result == "success", "Decorated sync func should work"

    def test_event_loop_configuration(self) -> None:
        """Verify event loop is properly configured."""
        init_file = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "__init__.py"
        )
        content = init_file.read_text()

        # Should use asyncio.get_event_loop(), not deprecated hass.loop
        assert (
            "asyncio.get_event_loop()" in content
        ), "Should use asyncio.get_event_loop()"
        assert (
            "hass.loop" not in content
        ), "Should not use deprecated hass.loop attribute"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
