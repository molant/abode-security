"""Vendored library path setup."""

from __future__ import annotations

import sys
from pathlib import Path

# Add vendored library path to BEGINNING of sys.path
# We vendor the Abode client library separately to avoid conflicts
_CANDIDATE_PATHS = [
    Path(__file__).resolve().parent / "lib",  # custom_components/abode_security/lib
    Path(__file__).resolve().parent.parent
    / "lib",  # custom_components/lib (legacy fallback)
    Path(__file__).resolve().parents[2] / "lib",  # repo-root/lib fallback
]

_VENDOR_PATH = next((path for path in _CANDIDATE_PATHS if path.exists()), None)
if _VENDOR_PATH is None:
    raise ImportError(
        f"Vendored Abode library not found. Expected one of: {', '.join(str(p) for p in _CANDIDATE_PATHS)}"
    )

_VENDOR_PATH_STR = str(_VENDOR_PATH)

# Add our vendored path at the very beginning
if _VENDOR_PATH_STR not in sys.path:
    sys.path.insert(0, _VENDOR_PATH_STR)

# Clear any cached imports of abode (but NOT abode_security) to force reload from our vendored path
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("abode") and not mod_name.startswith("abode_security"):
        del sys.modules[mod_name]
