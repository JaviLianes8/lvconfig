"""Typed coercion of stored string values.

LabVIEW writes booleans as ``TRUE`` or ``FALSE`` (and reads ``0`` and ``1`` as well),
and numbers in their plain text form including ``Inf`` and ``NaN``. These helpers turn
a decoded string into the Python type it stands for, raising on anything else.
"""

from __future__ import annotations

from ._errors import LvConfigError

_TRUE = {"true", "1"}
_FALSE = {"false", "0"}


def to_bool(value: str) -> bool:
    """Read a LabVIEW boolean: ``TRUE``/``FALSE`` (any case) or ``1``/``0``."""
    token = value.strip().lower()
    if token in _TRUE:
        return True
    if token in _FALSE:
        return False
    raise LvConfigError(f"not a LabVIEW boolean: {value!r}")


def to_int(value: str) -> int:
    """Read an integer value, raising ``LvConfigError`` when it is not one."""
    try:
        return int(value.strip())
    except ValueError as exc:
        raise LvConfigError(f"not an integer: {value!r}") from exc


def to_float(value: str) -> float:
    """Read a floating-point value, including LabVIEW's ``Inf`` and ``NaN``."""
    try:
        return float(value.strip())
    except ValueError as exc:
        raise LvConfigError(f"not a number: {value!r}") from exc
