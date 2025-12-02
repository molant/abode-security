"""Custom collection types for abode library."""


class RangeMap(dict):
    """
    A dict-like object that maps integer keys to values based on ranges.

    Keys define the start of each range (inclusive), extending to the next key (exclusive).
    This is a replacement for jaraco.collections.RangeMap using only Python stdlib.

    Examples:
        >>> rm = RangeMap({0: 'low', 100: 'medium', 200: 'high', 300: RangeMap.undefined_value})
        >>> rm[50]
        'low'
        >>> rm[150]
        'medium'
        >>> rm[250]
        Traceback (most recent call last):
        ...
        KeyError: 250
        >>> rm.get(250) is None
        True
    """

    undefined_value = object()

    def __getitem__(self, key):
        """Get value for key based on range mapping."""
        for range_start in sorted(self.keys(), reverse=True):
            if key >= range_start:
                value = super().__getitem__(range_start)
                if value is self.undefined_value:
                    raise KeyError(key)
                return value
        raise KeyError(key)

    def get(self, key, default=None):
        """Get value for key, returning default if not found."""
        try:
            return self[key]
        except KeyError:
            return default


class BijectiveMap(dict):
    """
    A bidirectional dictionary supporting both key->value and value->key lookups.

    This is a replacement for jaraco.collections.BijectiveMap using only Python stdlib.

    Examples:
        >>> bm = BijectiveMap(open=0, close=1, ping=2)
        >>> bm['open']
        0
        >>> bm[0]
        'open'
        >>> bm['ping']
        2
        >>> bm[2]
        'ping'
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._reverse = {v: k for k, v in kwargs.items()}

    def __getitem__(self, key):
        """Get value by key, or key by value."""
        try:
            return super().__getitem__(key)
        except KeyError:
            return self._reverse[key]

    def get(self, key, default=None):
        """Get value by key, or key by value, with default fallback."""
        try:
            return self[key]
        except KeyError:
            return default
