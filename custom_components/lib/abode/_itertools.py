"""Utilities for iterating and extracting from iterables."""


def always_iterable(obj, base_type=(str, bytes)):
    """
    Ensure obj is iterable. Strings and bytes are not considered iterable.

    If obj is already iterable (but not str/bytes), return it.
    Otherwise, wrap in a list.

    Examples:
        >>> list(always_iterable(None))
        []
        >>> list(always_iterable("string"))
        ['string']
        >>> list(always_iterable([1, 2]))
        [1, 2]
        >>> list(always_iterable(42))
        [42]
    """
    if obj is None:
        return []
    if isinstance(obj, base_type):
        return [obj]
    try:
        iter(obj)
        return obj
    except TypeError:
        return [obj]


def one(iterable):
    """
    Return the single item from iterable. Raises ValueError if not exactly one.

    Examples:
        >>> one([42])
        42
        >>> one([])
        Traceback (most recent call last):
        ...
        ValueError: too few items in iterable (expected 1)
        >>> one([1, 2])
        Traceback (most recent call last):
        ...
        ValueError: too many items in iterable (expected 1)
    """
    it = iter(iterable)
    try:
        value = next(it)
    except StopIteration:
        raise ValueError("too few items in iterable (expected 1)")

    try:
        next(it)
    except StopIteration:
        return value

    raise ValueError("too many items in iterable (expected 1)")


def only(iterable, default=None):
    """
    Return the single item from iterable or default if empty.
    Raises ValueError if multiple items present.

    Examples:
        >>> only([42])
        42
        >>> only([])
        >>> only([], 'default')
        'default'
        >>> only([1, 2])
        Traceback (most recent call last):
        ...
        ValueError: too many items in iterable (expected 0 or 1)
    """
    it = iter(iterable)
    try:
        value = next(it)
    except StopIteration:
        return default

    try:
        next(it)
    except StopIteration:
        return value

    raise ValueError("too many items in iterable (expected 0 or 1)")


def single(value):
    """Ensure value is a single item by converting to iterable and extracting one element."""
    return one(always_iterable(value))


def opt_single(value):
    """Extract optional single item from iterable, or None if empty."""
    return only(always_iterable(value))
