"""Root conftest for pytest-homeassistant-custom-component."""

from pathlib import Path
import sys

# Setup paths for custom_components and vendored libraries FIRST
# This must run before any imports from custom_components
_repo_root = Path(__file__).parent
_custom_components_path = str(_repo_root / "custom_components")
_vendor_path = str(_repo_root / "custom_components" / "lib")

# Add vendor path first (for vendored abode library)
if _vendor_path not in sys.path:
    sys.path.insert(0, _vendor_path)

# Add custom_components path (for integration discovery)
if _custom_components_path not in sys.path:
    sys.path.insert(0, _custom_components_path)
