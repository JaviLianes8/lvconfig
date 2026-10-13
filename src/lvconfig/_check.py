"""Argument checks and short, safe renderings of values for error messages."""

from __future__ import annotations

_LIMIT = 40


def short(value: str) -> str:
    """Return ``repr(value)`` cut to a bounded length, so messages never echo huge input.

    >>> short("abc")
    "'abc'"
    >>> short("x" * 100)
    "'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'... (100 characters)"
    """
    text = str.__str__(value)
    if len(text) <= _LIMIT:
        return repr(text)
    return f"{text[:_LIMIT]!r}... ({len(text)} characters)"


def type_name(value: object) -> str:
    """Return the name of ``value``'s type, cut to a bounded length."""
    name = type.__dict__["__name__"].__get__(type(value))
    name = str.__str__(name) if isinstance(name, str) else "object"
    return name if len(name) <= _LIMIT else name[:_LIMIT] + "..."


def need_str(what: str, value: object) -> str:
    """Return ``value`` as a plain ``str``, raising ``TypeError`` for anything else."""
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str, not {type_name(value)}")
    return str.__str__(value)


def need_bool(what: str, value: object) -> bool:
    """Return ``value`` if it is a ``bool``, raising ``TypeError`` otherwise."""
    if not isinstance(value, bool):
        raise TypeError(f"{what} must be a bool, not {type_name(value)}")
    return value


# LabVIEW folds the capitals of its Windows-1252 code page: A-Z, the Latin-1 capitals
# (not the sharp s or the multiplication sign) and S/Z caron, OE and Y diaeresis.
_UPPER = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    + "".join(chr(code) for code in range(0xC0, 0xDF) if code != 0xD7)
    + "\u0160\u0152\u017d\u0178"
)
_FOLD = str.maketrans(_UPPER, _UPPER.lower())


def fold(name: str) -> str:
    """Return ``name`` with its Windows-1252 capitals lower-cased, as names are compared.

    >>> fold("LVMode") == fold("lvmode")
    True
    """
    return name.translate(_FOLD)
