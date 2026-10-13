"""Typed reading of stored values, with the spellings LabVIEW 2026 itself accepts.

Every rule here was checked against LabVIEW's Read Key VIs (``tests/fixtures/labview2026``).
Where LabVIEW quietly reads a leading prefix (``12abc`` as 12, ``1_000`` as 1) these helpers
refuse the value instead, so a Python program never acts on a number nobody wrote.
"""

from __future__ import annotations

import re

from ._check import need_str, short
from ._errors import LvConfigError

_BLANKS = " \t"
_TRUE = frozenset({"true", "yes", "on", "t", "y", "1"})
_FALSE = frozenset({"false", "no", "off", "f", "0"})
_INT = re.compile(r"[+-]?[0-9]+")
_FLOAT = re.compile(r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)(?:[eE][+-]?[0-9]+)?")
_INF = re.compile(r"[+-]?inf(?:inity)?", re.IGNORECASE)


def to_bool(value: str) -> bool:
    """Read a LabVIEW boolean.

    ``TRUE``, ``yes``, ``on``, ``t``, ``y`` and ``1`` read as ``True``; ``FALSE``, ``no``,
    ``off``, ``f`` and ``0`` as ``False``; case is ignored and surrounding spaces and tabs
    too. These are exactly the spellings LabVIEW 2026's Read Key (Boolean) recognises.

    >>> to_bool("TRUE"), to_bool("off"), to_bool(" 1 ")
    (True, False, True)

    Raises :class:`LvConfigError` for anything else (LabVIEW would return its default),
    and ``TypeError`` when ``value`` is not a ``str``.
    """
    token = need_str("value", value).strip(_BLANKS).lower()
    if token in _TRUE:
        return True
    if token in _FALSE:
        return False
    raise LvConfigError(f"not a LabVIEW boolean: {short(value)}")


def to_int(value: str) -> int:
    """Read a whole decimal integer: an optional sign and ASCII digits.

    >>> to_int(" -42 "), to_int("007")
    (-42, 7)

    LabVIEW's Read Key (I32) reads only the leading digits of ``12abc``, ``3.7`` or
    ``1_000`` and clamps to 32 bits; this refuses such text, and keeps every digit.
    Raises :class:`LvConfigError` when the text is not an integer, and ``TypeError``
    when ``value`` is not a ``str``.
    """
    token = need_str("value", value).strip(_BLANKS)
    if not _INT.fullmatch(token):
        raise LvConfigError(f"not an integer: {short(value)}")
    try:
        return int(token)
    except ValueError as exc:  # more digits than Python converts by default
        raise LvConfigError(f"integer too long: {short(value)}") from exc


def to_float(value: str) -> float:
    """Read a floating-point number as LabVIEW's Read Key (Double) does.

    The decimal separator may be ``.`` or ``,`` (LabVIEW writes ``2,500000`` on a system
    whose separator is a comma), an exponent is allowed, and ``Inf``, ``Infinity`` and
    ``NaN`` are read in any case. A value too large for a double reads as infinity.

    >>> to_float("2,5"), to_float("1.5e-3"), to_float("-Inf")
    (2.5, 0.0015, -inf)

    Raises :class:`LvConfigError` for anything else, including the trailing text and
    hexadecimal forms LabVIEW cuts short, and ``TypeError`` when ``value`` is not a ``str``.
    """
    token = need_str("value", value).strip(_BLANKS)
    if _FLOAT.fullmatch(token):
        return float(token.replace(",", "."))
    if _INF.fullmatch(token):
        return float("-inf") if token.startswith("-") else float("inf")
    if token.lower() == "nan":
        return float("nan")
    raise LvConfigError(f"not a number: {short(value)}")
