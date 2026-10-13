"""One stored value, and how a Python value becomes one."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check import need_bool, need_str, type_name


@dataclass(frozen=True)
class Entry:
    """One stored value: its decoded text, whether it is quoted, and its comment lines.

    Quoted entries are strings and paths, which LabVIEW wraps in double quotes so edge
    whitespace survives. Unquoted entries are booleans and numbers, written as bare
    tokens. Both are escaped on write and unescaped on read. ``comments`` holds the
    verbatim comment lines that preceded the key on input, so a parsed file keeps its
    annotations through a dump.

    >>> Entry("TRUE", quoted=False)
    Entry(value='TRUE', quoted=False, comments=())

    Raises ``TypeError`` when ``value`` is not a ``str``, ``quoted`` not a ``bool`` or
    ``comments`` not a tuple of ``str``.
    """

    value: str
    quoted: bool
    comments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        need_str("value", self.value)
        need_bool("quoted", self.quoted)
        if not isinstance(self.comments, tuple):
            raise TypeError(f"comments must be a tuple, not {type_name(self.comments)}")
        for comment in self.comments:
            need_str("each comment", comment)


Value = str | bool | int | float


def make_entry(value: Value) -> Entry:
    """Turn a Python value into the entry LabVIEW would write for it."""
    if isinstance(value, bool):
        return Entry("TRUE" if value else "FALSE", quoted=False)
    if isinstance(value, int):
        # int.__repr__ ignores an override such as IntEnum's own __str__.
        return Entry(int.__repr__(value), quoted=False)
    if isinstance(value, float):
        # float.__repr__ reads the stored double, whatever a subclass overrides.
        text = float.__repr__(value)
        number = float(text)
        if math.isnan(number):
            return Entry("NaN", quoted=False)  # LabVIEW's spelling, not Python's
        if math.isinf(number):
            return Entry("Inf" if number > 0 else "-Inf", quoted=False)
        return Entry(text, quoted=False)
    if isinstance(value, str):
        return Entry(str.__str__(value), quoted=True)
    raise TypeError(f"value must be a str, bool, int or float, not {type_name(value)}")
