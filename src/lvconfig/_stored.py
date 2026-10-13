r"""The stored text of a value: what a line holds after its ``=``, read as LabVIEW reads it.

LabVIEW decodes ``\XX`` codes when it reads a string, but its typed and path reads work on
the stored text itself. So an :class:`Entry` made by :func:`parse` remembers the text it
came from, and one built in code gets the text lvconfig would write for it.
"""

from __future__ import annotations

from ._entry import Entry
from ._escape import escape, unescape

_BLANKS = " \t"  # LabVIEW trims spaces and tabs, nothing else


def is_quoted(text: str) -> bool:
    """Report whether ``text`` is wrapped in a pair of double or single quotes."""
    return len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'"


def body_of(right: str) -> str:
    """Return the value text of what follows the ``=``, trimmed as LabVIEW trims it."""
    body = right.strip(_BLANKS)
    if not is_quoted(body) and ";" in body:
        body = right.lstrip(_BLANKS)  # blanks after a comment are part of the value
    return body


def read(body: str) -> tuple[str, bool, str]:
    """Return ``(value, quoted, stored text)`` for a trimmed value text."""
    if is_quoted(body):
        return unescape(body[1:-1]), True, body[1:-1]
    # A bare ';' starts a comment: LabVIEW returns the value, trimmed, joined to it.
    before, semicolon, after = body.partition(";")
    stored = before.rstrip(_BLANKS) + semicolon + after
    return unescape(stored), False, stored


def remember(entry: Entry, stored: str) -> Entry:
    """Attach the stored text a parsed entry came from; it takes no part in equality."""
    object.__setattr__(entry, "_stored", stored)
    return entry


def stored(entry: Entry) -> str:
    """Return the text between the quotes, or the bare token, that ``entry`` stands for."""
    text = entry.__dict__.get("_stored")
    if isinstance(text, str):
        return text
    text = escape(entry.value)
    # A bare tab is trimmed or kept by position; its code reads back the same everywhere.
    return text if entry.quoted else text.replace("\t", "\\09")


def render(entry: Entry) -> str:
    """Return the text written after ``key = `` for ``entry``."""
    text = stored(entry)
    return f'"{text}"' if entry.quoted else text


def reads_back(entry: Entry) -> bool:
    """Report whether the rendered entry reads back as the same value and quoting."""
    value, quoted, _ = read(body_of(render(entry)))
    return (value, quoted) == (entry.value, entry.quoted)
