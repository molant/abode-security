"""Tests for the aioresponses/aiohttp 3.14 compatibility shim.

Every test that mocks HTTP depends on `tests/aioresponses_compat.apply()`
having run (it is invoked from the root `conftest.py`). Without these tests a
regression in the shim surfaces as hundreds of unrelated failures with a
confusing `ClientResponse.__init__()` traceback; with them it surfaces here,
named.

The large-body case is the one no other test covers: `StreamReader` only calls
the protocol flow-control hooks the shim stubs out once a payload exceeds its
64 KiB limit, so a small fixture never exercises that half.
"""

import aiohttp
import aioresponses.core as aioresponses_core
import pytest
from aiohttp.client_reqrep import ClientResponse
from aioresponses import aioresponses
from packaging.version import Version

import tests.aioresponses_compat as compat
from tests.aioresponses_compat import (
    LAST_UNPATCHED_AIORESPONSES,
    installed_aioresponses_version,
)

URL = "http://example.test/payload"


async def test_small_body_round_trips() -> None:
    """A mocked response builds and reads back — the `stream_writer` half."""
    with aioresponses() as mocked:
        mocked.get(URL, status=200, body="hello")

        async with aiohttp.ClientSession() as session, session.get(URL) as response:
            assert response.status == 200
            assert await response.text() == "hello"


async def test_body_larger_than_stream_reader_limit_round_trips() -> None:
    """A body over StreamReader's 64 KiB limit reads back whole.

    This is the `stream_reader_factory` half: over the limit, `StreamReader`
    reaches into `protocol._parser`, which does not exist behind a mocked
    response unless the shim stubs it.
    """
    body = b"x" * (1024 * 1024)

    with aioresponses() as mocked:
        mocked.get(URL, status=200, body=body)

        async with aiohttp.ClientSession() as session, session.get(URL) as response:
            assert await response.read() == body


def test_shim_is_still_needed_for_the_installed_aioresponses() -> None:
    """Assert the installed aioresponses is still one the shim should patch.

    Belt-and-braces: on aiohttp >= 3.14 the root `conftest.py` calls `apply()`
    before collection, so a too-new aioresponses already fails there and this
    never runs. It earns its place on aiohttp < 3.14, where `apply()` returns
    early and the version boundary would otherwise go unchecked.
    """
    installed = installed_aioresponses_version()

    assert installed <= LAST_UNPATCHED_AIORESPONSES, (
        f"aioresponses {installed} is newer than the shimmed "
        f"{LAST_UNPATCHED_AIORESPONSES}. Check whether it now supports aiohttp "
        "3.14 natively — if so, delete tests/aioresponses_compat.py and its "
        "call in conftest.py."
    )


class _AiohttpThatNeedsTheShim:
    """Stand-in for aiohttp 3.14+'s `ClientResponse.__init__` signature.

    Only its signature matters: `apply()` decides whether to patch by asking
    whether `stream_writer` is a parameter.
    """

    def __init__(self, *args: object, stream_writer: object = None, **kwargs: object):
        pass


@pytest.fixture
def aiohttp_needs_shim(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin `apply()`'s aiohttp-version check to the "shim required" branch.

    Without this the guard tests silently depend on the ambient aiohttp: on
    anything before 3.14 `apply()` early-returns, so it neither raises for a
    too-new aioresponses nor patches for a supported one, and both guard tests
    fail for a reason unrelated to what they assert. HA pins 3.14.3 today, but
    this file's own `test_shim_is_still_needed_for_the_installed_aioresponses`
    treats aiohttp < 3.14 as a live scenario, so the tests should not assume
    otherwise.

    Also resets `aioresponses.core.ClientResponse` to the stock class, so an
    assertion that it ends up patched observes a real transition rather than
    the state the root `conftest.py` already established at import time.
    """
    monkeypatch.setattr(compat, "ClientResponse", _AiohttpThatNeedsTheShim)
    monkeypatch.setattr(aioresponses_core, "ClientResponse", ClientResponse)


@pytest.mark.parametrize(
    "version",
    [
        "0.7.9.post1",  # packaging-only re-release, still newer
        "0.7.9+local",  # locally rebuilt wheel
        "0.7.10rc1",  # pre-release of a newer patch
        "0.7.10",
        "0.8.0.dev1",
        "1.0.0",
    ],
)
@pytest.mark.usefixtures("aiohttp_needs_shim")
def test_apply_refuses_to_patch_a_newer_aioresponses(
    version: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every version above the shimmed one must make `apply()` refuse.

    Drives the real predicate rather than asserting on `Version.__gt__`: this
    is what catches the comparison being inverted or the guard being deleted.
    Post-releases and local versions are the forms that must not slip through
    as "equal" to the shimmed release.
    """
    monkeypatch.setattr(
        compat, "installed_aioresponses_version", lambda: Version(version)
    )

    with pytest.raises(RuntimeError, match="is newer than"):
        compat.apply()

    # The refusal must be total — no half-applied patch left behind.
    assert getattr(aioresponses_core, "ClientResponse") is ClientResponse


@pytest.mark.parametrize("version", ["0.7.9", "0.7.8", "0.7.9rc1"])
@pytest.mark.usefixtures("aiohttp_needs_shim")
def test_apply_still_patches_the_shimmed_release(
    version: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At or below the shimmed release, `apply()` patches instead of raising."""
    monkeypatch.setattr(
        compat, "installed_aioresponses_version", lambda: Version(version)
    )

    compat.apply()

    # `getattr` for the same reason `apply()` uses `setattr`: the name is a
    # re-export inside `aioresponses.core`, which type checkers treat as private.
    patched = getattr(aioresponses_core, "ClientResponse")
    assert patched is compat._StreamWriterClientResponse


def test_unparseable_installed_version_raises_with_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-PEP-440 version surfaces this module's error, not `InvalidVersion`.

    `apply()` runs at conftest import time, where a bare `InvalidVersion`
    traceback would carry none of the remediation guidance.
    """
    monkeypatch.setattr(compat, "aioresponses_version", lambda _name: "not-a-version")

    with pytest.raises(RuntimeError, match="PEP 440"):
        compat.installed_aioresponses_version()
