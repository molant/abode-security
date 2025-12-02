"""Utility for iterating class hierarchies."""


def iter_subclasses(cls):
    """
    Recursively yield all subclasses of a class.

    This is a replacement for jaraco.classes.ancestry.iter_subclasses,
    using only the Python standard library.

    Examples:
        >>> class A:
        ...     pass
        >>> class B(A):
        ...     pass
        >>> class C(B):
        ...     pass
        >>> list(iter_subclasses(A))
        [<class 'B'>, <class 'C'>]
    """
    for subclass in cls.__subclasses__():
        yield subclass
        yield from iter_subclasses(subclass)
