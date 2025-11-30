import jaraco.itertools
import more_itertools


def single(value):
    """Ensure value is a single item by converting to iterable and extracting one element."""
    return more_itertools.one(jaraco.itertools.always_iterable(value))


def opt_single(value):
    """Extract optional single item from iterable, or None if empty."""
    return more_itertools.only(jaraco.itertools.always_iterable(value))
