"""Vendored library path setup."""

from __future__ import annotations

import sys
from pathlib import Path

# Add vendored library path to BEGINNING of sys.path
# We vendor the Abode client library separately to avoid conflicts
_VENDOR_PATH = Path(__file__).parent.parent / "lib"
_VENDOR_PATH_STR = str(_VENDOR_PATH)

# Add our vendored path at the very beginning
if _VENDOR_PATH_STR not in sys.path:
    sys.path.insert(0, _VENDOR_PATH_STR)

# Clear any cached imports of abode to force reload from our vendored path
import importlib
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith('abode'):
        del sys.modules[mod_name]
