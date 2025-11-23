"""Vendored library path setup."""

from __future__ import annotations

import sys
from pathlib import Path

# Add vendored library path
_VENDOR_PATH = Path(__file__).parent.parent.parent / "lib"
if str(_VENDOR_PATH) not in sys.path:
    sys.path.insert(0, str(_VENDOR_PATH))
