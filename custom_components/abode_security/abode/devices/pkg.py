import functools
import importlib

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files


def _removesuffix(string, suffix):
    """Remove suffix from string, with fallback for Python < 3.9."""
    if hasattr(string, 'removesuffix'):
        return string.removesuffix(suffix)
    if suffix and string.endswith(suffix):
        return string[:-len(suffix)]
    return string


@functools.lru_cache
def import_all():
    """Import all modules from this package."""
    device_mods = (
        _removesuffix(mod.name, '.py')
        for mod in files(__package__).iterdir()
        if mod.name != '__init__.py'
    )
    for mod in device_mods:
        importlib.import_module(f'.{mod}', __package__)
