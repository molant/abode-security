"""Static analysis of async/await patterns without runtime imports.

This test performs static code analysis to verify async/await fixes
are present in the code without requiring full module imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


class AsyncAwaitStaticAnalyzer:
    """Analyze async/await patterns in Python code."""

    def __init__(self, code: str, filename: str = ""):
        """Initialize analyzer with Python source code."""
        self.code = code
        self.filename = filename
        self.tree = ast.parse(code)

    def find_async_functions(self) -> dict[str, bool]:
        """Find all async function definitions and their locations."""
        async_funcs = {}

        for node in ast.walk(self.tree):
            if isinstance(node, ast.AsyncFunctionDef):
                async_funcs[node.name] = True
            elif isinstance(node, ast.FunctionDef):
                async_funcs[node.name] = False

        return async_funcs

    def function_contains_await(self, func_name: str) -> bool:
        """Check if a function contains any await statements."""
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):  # noqa: SIM102
                if node.name == func_name:
                    for child in ast.walk(node):
                        if isinstance(child, ast.Await):
                            return True
        return False

    def count_await_statements(self) -> int:
        """Count total await statements in the code."""
        count = 0
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Await):
                count += 1
        return count

    def find_async_properties(self) -> list[str]:
        """Find invalid async property definitions."""
        invalid = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.AsyncFunctionDef):
                # Check if it has @property decorator
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "property":
                        invalid.append(node.name)

        return invalid

    def find_asyncio_run_calls(self) -> list[int]:
        """Find uses of asyncio.run() in the code."""
        calls = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):  # noqa: SIM102
                if isinstance(node.func, ast.Attribute) and (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "asyncio"
                    and node.func.attr == "run"
                ):
                    calls.append(node.lineno)

        return calls

    def find_run_until_complete_calls(self) -> list[int]:
        """Find uses of run_until_complete() in the code."""
        calls = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):  # noqa: SIM102
                if isinstance(node.func, ast.Attribute):  # noqa: SIM102
                    if node.func.attr == "run_until_complete":
                        calls.append(node.lineno)

        return calls

    def find_wait_for_calls(self) -> list[int]:
        """Find asyncio.wait_for() calls."""
        calls = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):  # noqa: SIM102
                if isinstance(node.func, ast.Attribute) and (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "asyncio"
                    and node.func.attr == "wait_for"
                ):
                    calls.append(node.lineno)

        return calls


class TestAsyncAwaitStaticPatterns:
    """Test async/await patterns via static analysis."""

    @pytest.fixture
    def services_file(self) -> str:
        """Load services.py file."""
        path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "services.py"
        )
        return path.read_text()

    @pytest.fixture
    def entity_file(self) -> str:
        """Load entity.py file."""
        path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "entity.py"
        )
        return path.read_text()

    @pytest.fixture
    def init_file(self) -> str:
        """Load __init__.py file."""
        path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "__init__.py"
        )
        return path.read_text()

    @pytest.fixture
    def camera_file(self) -> str:
        """Load camera.py file."""
        path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "camera.py"
        )
        return path.read_text()

    @pytest.fixture
    def switch_file(self) -> str:
        """Load switch.py file."""
        path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "switch.py"
        )
        return path.read_text()

    def test_service_handler_signatures(self, services_file: str) -> None:
        """Verify service handler function signatures are correct."""
        analyzer = AsyncAwaitStaticAnalyzer(services_file, "services.py")
        async_funcs = analyzer.find_async_functions()

        # These should be async
        assert async_funcs.get("_change_setting") is True, (
            "_change_setting should be async def"
        )
        assert async_funcs.get("_trigger_alarm_handler") is True, (
            "_trigger_alarm_handler should be async def"
        )

        # These should be sync
        assert async_funcs.get("_capture_image") is False, (
            "_capture_image should be sync def"
        )
        assert async_funcs.get("_trigger_automation") is False, (
            "_trigger_automation should be sync def"
        )

    def test_service_handlers_have_correct_await_usage(
        self, services_file: str
    ) -> None:
        """Verify service handlers use await correctly."""
        analyzer = AsyncAwaitStaticAnalyzer(services_file, "services.py")

        # Async handlers should have await
        assert analyzer.function_contains_await("_change_setting"), (
            "_change_setting should contain await"
        )
        assert analyzer.function_contains_await("_trigger_alarm_handler"), (
            "_trigger_alarm_handler should contain await"
        )

        # Sync handlers should not have await
        assert not analyzer.function_contains_await("_capture_image"), (
            "_capture_image should not contain await"
        )
        assert not analyzer.function_contains_await("_trigger_automation"), (
            "_trigger_automation should not contain await"
        )

    def test_factory_handler_is_async(self, services_file: str) -> None:
        """Verify service handler factory creates async handler."""
        analyzer = AsyncAwaitStaticAnalyzer(services_file, "services.py")
        analyzer.find_async_functions()

        # The handler function inside _create_service_handler should be async
        # We'll check the factory itself returns an async handler
        assert "handler" in services_file, (
            "_create_service_handler should define handler"
        )
        assert "async def handler" in services_file, "handler should be async def"

    def test_entity_has_async_lifecycle_methods(self, entity_file: str) -> None:
        """Verify entity lifecycle methods are async."""
        analyzer = AsyncAwaitStaticAnalyzer(entity_file, "entity.py")
        async_funcs = analyzer.find_async_functions()

        # These should be async
        expected_async = [
            "async_added_to_hass",
            "async_will_remove_from_hass",
            "async_update",
        ]

        for func_name in expected_async:
            assert async_funcs.get(func_name) is True, (
                f"{func_name} should be async def"
            )

    def test_timeout_protection_in_entity(self, entity_file: str) -> None:
        """Verify executor jobs have timeout protection."""
        analyzer = AsyncAwaitStaticAnalyzer(entity_file, "entity.py")
        wait_for_calls = analyzer.find_wait_for_calls()

        # Should have multiple asyncio.wait_for calls
        assert len(wait_for_calls) >= 4, (
            f"Entity should have at least 4 asyncio.wait_for calls, "
            f"found {len(wait_for_calls)}"
        )

    def test_no_asyncio_run_in_integration(self) -> None:
        """Verify integration doesn't use asyncio.run()."""
        import_dir = (
            Path(__file__).parent.parent / "custom_components" / "abode_security"
        )

        for py_file in import_dir.glob("*.py"):
            content = py_file.read_text()
            analyzer = AsyncAwaitStaticAnalyzer(content, py_file.name)
            run_calls = analyzer.find_asyncio_run_calls()

            assert len(run_calls) == 0, f"{py_file.name} should not use asyncio.run()"

    def test_no_run_until_complete_in_integration(self) -> None:
        """Verify integration doesn't use run_until_complete()."""
        import_dir = (
            Path(__file__).parent.parent / "custom_components" / "abode_security"
        )

        for py_file in import_dir.glob("*.py"):
            content = py_file.read_text()
            analyzer = AsyncAwaitStaticAnalyzer(content, py_file.name)
            run_calls = analyzer.find_run_until_complete_calls()

            assert len(run_calls) == 0, (
                f"{py_file.name} should not use run_until_complete()"
            )

    def test_no_async_properties_in_integration(self) -> None:
        """Verify no async properties (invalid pattern)."""
        import_dir = (
            Path(__file__).parent.parent / "custom_components" / "abode_security"
        )

        for py_file in import_dir.glob("*.py"):
            content = py_file.read_text()
            analyzer = AsyncAwaitStaticAnalyzer(content, py_file.name)
            async_props = analyzer.find_async_properties()

            assert len(async_props) == 0, (
                f"{py_file.name} has invalid async properties: {async_props}"
            )

    def test_camera_has_dispatcher_cleanup(self, camera_file: str) -> None:
        """Verify camera uses async_on_remove for dispatcher cleanup."""
        assert "async_on_remove" in camera_file, "camera.py should use async_on_remove"
        assert "async_dispatcher_connect" in camera_file, (
            "camera.py should use async_dispatcher_connect"
        )

    def test_switch_has_async_task_wrapping(self, switch_file: str) -> None:
        """Verify switch properly wraps async callbacks."""
        assert "async_create_task" in switch_file, (
            "switch.py should use async_create_task"
        )

    def test_init_uses_modern_event_loop(self, init_file: str) -> None:
        """Verify __init__.py uses modern event loop API."""
        assert "asyncio.get_event_loop()" in init_file, (
            "__init__.py should use asyncio.get_event_loop()"
        )

        # Should not use deprecated hass.loop
        assert "hass.loop" not in init_file, "__init__.py should not use hass.loop"

    def test_timeout_protection_pattern(self, entity_file: str) -> None:
        """Verify timeout protection pattern with try/except."""
        # Count asyncio.wait_for calls
        wait_for_count = entity_file.count("asyncio.wait_for(")
        assert wait_for_count >= 4, (
            f"Expected at least 4 asyncio.wait_for calls, found {wait_for_count}"
        )

        # Should have timeout parameter
        assert "timeout=" in entity_file, "asyncio.wait_for should have timeout"

        # Should have TimeoutError handling
        assert "TimeoutError" in entity_file, "Should handle asyncio.TimeoutError"


class TestAsyncAwaitDocumentation:
    """Test that async/await patterns are documented."""

    def test_service_handlers_have_docstrings(self) -> None:
        """Verify service handlers have docstring explanations."""
        services_file = (
            Path(__file__).parent.parent
            / "custom_components"
            / "abode_security"
            / "services.py"
        )
        content = services_file.read_text()

        # Check for docstring on _capture_image
        assert "dispatcher_send()" in content and "sync" in content.lower(), (
            "Service handlers should document why they are sync/async"
        )

    def test_async_patterns_documented(self) -> None:
        """Verify async patterns are documented in code."""
        docs_file = Path(__file__).parent.parent / "docs" / "ASYNC_AWAIT_PATTERNS.md"

        if docs_file.exists():
            content = docs_file.read_text()
            # Verify documentation exists
            assert "async" in content.lower(), (
                "Documentation should cover async patterns"
            )
            assert "await" in content.lower(), (
                "Documentation should cover await patterns"
            )


class TestAsyncAwaitIntegration:
    """Integration-level async/await tests."""

    def test_all_platform_files_are_valid_python(self) -> None:
        """Verify all platform files are valid Python."""
        import_dir = (
            Path(__file__).parent.parent / "custom_components" / "abode_security"
        )

        for py_file in import_dir.glob("*.py"):
            try:
                ast.parse(py_file.read_text())
            except SyntaxError as e:
                pytest.fail(f"{py_file.name} has syntax error: {e}")

    def test_all_test_files_are_valid_python(self) -> None:
        """Verify all test files are valid Python."""
        test_dir = Path(__file__).parent

        for py_file in test_dir.glob("test_*.py"):
            try:
                ast.parse(py_file.read_text())
            except SyntaxError as e:
                pytest.fail(f"{py_file.name} has syntax error: {e}")

    def test_async_await_line_count(self) -> None:
        """Verify significant async/await coverage."""
        import_dir = (
            Path(__file__).parent.parent / "custom_components" / "abode_security"
        )

        total_awaits = 0
        total_asyncs = 0

        for py_file in import_dir.glob("*.py"):
            content = py_file.read_text()
            total_awaits += content.count("await ")
            total_asyncs += content.count("async def")

        # Should have substantial async coverage
        assert total_asyncs > 20, f"Expected 20+ async functions, found {total_asyncs}"
        assert total_awaits > 50, f"Expected 50+ await statements, found {total_awaits}"

        print("\nIntegration Stats:")
        print(f"  Total async functions: {total_asyncs}")
        print(f"  Total await statements: {total_awaits}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
