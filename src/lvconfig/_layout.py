"""The source layout :func:`parse` records so :func:`dump` can reproduce it exactly.

A LabVIEW configuration file carries more than its values: blank lines, comment
styles, ``key = value`` spacing, line endings, a missing final newline, repeated
sections and a byte order mark. :class:`Layout` keeps every source line verbatim and
remembers what each key line held when it was read, so an untouched line is written
back byte for byte and only an edited key is rewritten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ._entry import Entry

_EOL = re.compile(r"\r\n|\n|\r")


@dataclass(frozen=True)
class RawLine:
    """One source line: its text without the terminator, and the terminator itself.

    ``eol`` is ``"\\r\\n"``, ``"\\n"``, ``"\\r"``, or ``""`` for a last line that
    has no newline.
    """

    text: str
    eol: str


@dataclass(frozen=True)
class HeaderItem:
    """A ``[section]`` line and the blank and comment lines just above it."""

    name: str
    lead: tuple[RawLine, ...]
    line: RawLine


@dataclass(frozen=True)
class KeyItem:
    """A ``key=value`` line, the lines above it, and the entry it held when read.

    ``prefix`` is the source text before the value (``"Name = "``) and ``suffix`` the
    whitespace after it, so an edited value keeps the original spacing. ``shadowed``
    marks a key that a later line of the same section redefines.
    """

    section: str
    key: str
    lead: tuple[RawLine, ...]
    line: RawLine
    prefix: str
    suffix: str
    entry: Entry
    shadowed: bool = False
    behind_blank: bool = False


@dataclass(frozen=True)
class Layout:
    """Everything needed to write a parsed file back unchanged.

    ``headers`` and ``trailing`` snapshot the comment lines as parsed, so a caller
    who edits ``Config.header_comments`` or ``Config.trailing_comments`` sees the
    edit honoured. ``eol`` is the line ending used for newly written lines and
    ``final_eol`` the terminator of the source's last line.
    """

    items: tuple[HeaderItem | KeyItem, ...]
    tail: tuple[RawLine, ...]
    headers: dict[str, tuple[str, ...]]
    trailing: tuple[str, ...]
    bom: str
    eol: str
    final_eol: str


def split_lines(text: str) -> list[RawLine]:
    """Split ``text`` into lines, keeping each line's own terminator."""
    lines: list[RawLine] = []
    pos = 0
    for match in _EOL.finditer(text):
        lines.append(RawLine(text[pos : match.start()], match.group()))
        pos = match.end()
    if pos < len(text):
        lines.append(RawLine(text[pos:], ""))
    return lines


def is_comment(stripped: str) -> bool:
    """Report whether a stripped line is a whole-line ``;`` or ``#`` comment."""
    return stripped.startswith((";", "#"))
