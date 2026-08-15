"""Compatibility shim making `aioresponses` work against aiohttp 3.14+.

aiohttp 3.14 added a required keyword-only `stream_writer` argument to
`ClientResponse.__init__`, and made `StreamReader` call flow-control hooks on
the owning protocol once a payload exceeds its limit. `aioresponses` 0.7.9 —
the latest release, and the last one before the project went quiet in April
2026 — predates both, so every mocked request raises:

    ClientResponse.__init__() missing 1 required keyword-only argument:
    'stream_writer'

Home Assistant pins aiohttp exactly (2026.8.2 → 3.14.3), and that pin is what
clears the aiohttp advisories the `pip-audit` CI job fails on, so downgrading
aiohttp is not an option. The fixes exist upstream but only as unmerged pull
requests:

    https://github.com/pnuckowski/aioresponses/pull/288  (stream_writer)
    https://github.com/pnuckowski/aioresponses/pull/292  (pause_reading)

This module ports both, applied by monkeypatching the two names
`aioresponses.core` resolves at call time. Nothing outside `aioresponses` is
touched: real `aiohttp` code paths keep the stock `ClientResponse` and
`StreamReader`. Delete this file and the `apply()` call in the root
`conftest.py` once an `aioresponses` release ships aiohttp 3.14 support.
"""

from __future__ import annotations

import inspect
from importlib.metadata import version as aioresponses_version
from typing import Any
from unittest.mock import Mock

import aioresponses.core
from aiohttp import StreamReader
from aiohttp.client_proto import ResponseHandler
from aiohttp.client_reqrep import ClientResponse
from packaging.version import InvalidVersion, Version


class _StreamWriterClientResponse(ClientResponse):
    """`ClientResponse` that supplies aiohttp 3.14's `stream_writer` argument.

    aiohttp only reads `stream_writer.output_size`, so a `Mock` reporting zero
    bytes written is sufficient for a response that was never really sent.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("stream_writer", Mock(output_size=0))
        super().__init__(*args, **kwargs)


def _stream_reader_factory(loop: Any = None) -> StreamReader:
    """Build a `StreamReader` whose protocol tolerates over-limit payloads.

    A body larger than the reader's limit makes `StreamReader` invoke the
    protocol's flow-control hooks, which on aiohttp 3.14 reach into
    `protocol._parser`. There is no real parser behind a mocked response, so
    stub one that yields nothing.

    `loop` is typed `Any` because `aioresponses` passes the `Mock` it uses in
    place of an event loop, not a real `AbstractEventLoop`.
    """
    protocol = ResponseHandler(loop=loop)
    protocol._parser = Mock()
    protocol._parser.feed_data.return_value = ([], False, b"")
    return StreamReader(protocol, limit=2**16, loop=loop)


# Last aioresponses release known to need this shim. Above it, assume upstream
# shipped its own aiohttp 3.14 support: continuing to patch would replace the
# real implementation with a subclass of the *stock* `ClientResponse` and
# silently discard whatever upstream now does.
#
# A `packaging.version.Version` rather than a hand-rolled tuple, so the
# ordering is full PEP 440 — post-releases (`0.7.9.post1`) and local versions
# (`0.7.9+local`) sort above the plain release and trip the guard, which a
# "split on dots, take three ints" parser gets wrong by collapsing both to
# equality.
LAST_UNPATCHED_AIORESPONSES = Version("0.7.9")


def installed_aioresponses_version() -> Version:
    """Version of the installed aioresponses.

    Single source of truth for both `apply()` and the tests, so the runtime
    guard and the test assertion cannot disagree about what is installed.

    Raises `RuntimeError` if the installed metadata is not PEP 440 — rather
    than letting a bare `InvalidVersion` escape, since `apply()` runs at
    `conftest.py` import time where a raw traceback carries none of this
    module's remediation guidance.
    """
    raw = aioresponses_version("aioresponses")
    try:
        return Version(raw)
    except InvalidVersion as exc:
        raise RuntimeError(
            f"Cannot parse the installed aioresponses version {raw!r} as PEP "
            "440, so this shim cannot tell whether it is still needed. Check "
            "the install, then see tests/aioresponses_compat.py."
        ) from exc


def apply() -> None:
    """Patch `aioresponses` for aiohttp 3.14+. A no-op on older aiohttp."""
    if "stream_writer" not in inspect.signature(ClientResponse).parameters:
        return

    installed = installed_aioresponses_version()
    if installed > LAST_UNPATCHED_AIORESPONSES:
        raise RuntimeError(
            f"aioresponses {installed} is newer than the "
            f"{LAST_UNPATCHED_AIORESPONSES} this shim was written against. "
            "Check whether it now supports aiohttp 3.14 natively; if so "
            "delete tests/aioresponses_compat.py and its call in conftest.py, "
            "otherwise raise LAST_UNPATCHED_AIORESPONSES."
        )

    # Assert before patching: `setattr` on a renamed or relocated symbol would
    # quietly create a new unused attribute and surface far from the cause.
    for name in ("ClientResponse", "stream_reader_factory"):
        if not hasattr(aioresponses.core, name):
            raise RuntimeError(
                f"aioresponses.core has no {name!r} to patch — its internals "
                "changed, so this shim needs revisiting."
            )

    # `setattr` rather than direct assignment: both names are re-exports inside
    # `aioresponses.core`, which type checkers treat as private.
    setattr(aioresponses.core, "ClientResponse", _StreamWriterClientResponse)
    setattr(aioresponses.core, "stream_reader_factory", _stream_reader_factory)
