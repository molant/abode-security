"""Pin the Dependabot contract that keeps `uv.lock` maintained (issue #218).

CI installs with `uv sync --locked`, and the pip-audit job scans an export of
`uv.lock` — so the lockfile, not `pyproject.toml`, is what has to stay current.
Dependabot's `pip` ecosystem only rewrites `pyproject.toml`, which left every
Python bump PR failing `uv sync --locked` on arrival (#170, #173, #176, #199,
#215) and left lockfile-only transitive packages with no bump path at all.
`pip` 26.1.2 sat on PYSEC-2026-3721 until it was cleared by hand, because that
advisory has no GHSA entry and so never reached Dependabot's security updates
either.

The `uv` ecosystem maintains `uv.lock` alongside `pyproject.toml`, and
`allow: dependency-type: all` extends version updates to the dependencies of
direct dependencies — a path that does not depend on the GitHub Advisory
Database at all. These tests keep that wiring from silently reverting.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

CONFIG = Path(__file__).parent.parent / ".github" / "dependabot.yml"


@pytest.fixture(name="python_updater")
def python_updater_fixture() -> dict[str, Any]:
    """The updater responsible for the root Python project."""
    config: dict[str, Any] = yaml.safe_load(CONFIG.read_text())
    updates: list[dict[str, Any]] = config["updates"]
    python_updaters = [
        update
        for update in updates
        if update["package-ecosystem"] in {"pip", "uv"} and update["directory"] == "/"
    ]
    assert len(python_updaters) == 1, (
        "expected exactly one Python updater for the root directory, "
        f"found {len(python_updaters)}"
    )
    return python_updaters[0]


def test_python_updater_maintains_the_lockfile(python_updater: dict[str, Any]) -> None:
    """`pip` only rewrites pyproject.toml; CI resolves against uv.lock."""
    assert python_updater["package-ecosystem"] == "uv", (
        "the Python updater must use the `uv` ecosystem so bump PRs regenerate "
        "uv.lock — `pip` edits pyproject.toml alone, which fails `uv sync --locked`"
    )


def test_python_updater_covers_transitive_dependencies(
    python_updater: dict[str, Any],
) -> None:
    """Lockfile-only packages need a version-update path of their own."""
    allowed = {
        entry.get("dependency-type") for entry in python_updater.get("allow", [])
    }
    assert "all" in allowed, (
        "the Python updater must allow `dependency-type: all` so transitive "
        "packages that exist only in uv.lock (pip, pipdeptree, ...) get bumped "
        "without waiting on a GitHub Advisory Database entry"
    )


def test_pyturbojpeg_ignore_survives(python_updater: dict[str, Any]) -> None:
    """PyTurboJPEG tracks HA's exact pin — Dependabot must not push past 1.x."""
    ignored = {
        entry["dependency-name"]: entry["versions"]
        for entry in python_updater.get("ignore", [])
    }
    assert ignored.get("pyturbojpeg") == [">=2.0"], (
        "the pyturbojpeg ignore must stay, in PEP 440 specifier form — the "
        "`2.x` wildcard makes Dependabot reject the whole config file"
    )


def test_grouping_survives(python_updater: dict[str, Any]) -> None:
    """`pytest-homeassistant-custom-component` stays out of the dev-deps group."""
    groups = python_updater["groups"]
    assert groups["dev-deps"]["exclude-patterns"] == [
        "pytest-homeassistant-custom-component"
    ]
    assert groups["ha-pin"]["patterns"] == ["pytest-homeassistant-custom-component"]
