"""Regression test for issue #74: the phase-4.5 allowlist must not return.

`tests/conftest.py` used to carry an `enabled_tests` set plus a
`pytest_collection_modifyitems` hook that silently skipped any test using the
`hass` fixture (transitively, in practice every test) unless its name was in
the allowlist. That made the suite report ~119 silent skips and meant
newly-added tests could silently skip without any signal. Issue #74 removed
the mechanism; this test guards against accidental reintroduction.
"""

from pathlib import Path


def test_conftest_has_no_phase45_allowlist() -> None:
    """`tests/conftest.py` must not contain the phase-4-5 skip allowlist."""
    content = Path(__file__).parent.joinpath("conftest.py").read_text()
    # Anchor on the specific token shapes that defined the mechanism, not bare
    # substrings — that way a future commit can mention the historical name in
    # a comment without tripping this guard.
    assert "enabled_tests = {" not in content, (
        "Issue #74: the `enabled_tests` allowlist must not be reintroduced. "
        "If you need to skip a test, mark it explicitly with @pytest.mark.skip."
    )
    assert "def pytest_collection_modifyitems" not in content, (
        "Issue #74: the collection-modifying skip hook must not be reintroduced."
    )
    assert "Test infrastructure complete but test needs updates" not in content, (
        "Issue #74: the phase-4-5.md skip-reason text must not be reintroduced."
    )
