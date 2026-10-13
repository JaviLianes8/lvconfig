"""Checks that a config can be written as text that reads back as the same config.

A key holding ``=`` or a line break, a bare value wrapped in quotes, or a comment
that does not start with ``;`` or ``#`` would be written fine but read back as
something else. These checks raise :class:`LvConfigError` instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._errors import LvConfigError

if TYPE_CHECKING:
    from ._config import Config
    from ._entry import Entry

_BREAKS = ("\r", "\n")
_BLANKS = " \t"


def check_section(name: str) -> None:
    """Refuse a section name that cannot be written as one ``[name]`` line."""
    if any(char in name for char in _BREAKS):
        raise LvConfigError(f"section name {name!r} contains a line break")


def check_key(key: str, entry: Entry) -> None:
    """Refuse a key that would read back as a different key, a comment or a header."""
    if "=" in key or any(char in key for char in _BREAKS):
        raise LvConfigError(f"key {key!r} contains '=' or a line break")
    if key != key.strip(_BLANKS):
        raise LvConfigError(f"key {key!r} has leading or trailing whitespace")
    if key.startswith((";", "#")):
        raise LvConfigError(f"key {key!r} starts with ';' or '#'")
    if key.startswith("[") and not entry.quoted and entry.value.endswith("]"):
        raise LvConfigError(f"key {key!r} with value {entry.value!r} reads as a header")
    check_entry(key, entry)


def is_bare_safe(value: str) -> bool:
    """Report whether ``value`` reads back unchanged when written without quotes.

    LabVIEW trims spaces and tabs around a bare token, removes a pair of quotes around
    it, and treats a ``;`` in it as the start of a comment, so a bare value must have
    none of those.
    """
    if value != value.strip(_BLANKS) or ";" in value:
        return False
    return not (len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'")


def check_entry(key: str, entry: Entry) -> None:
    """Refuse an entry whose bare value or comments would not read back as stored."""
    if not entry.quoted and not is_bare_safe(entry.value):
        raise LvConfigError(f"bare value of {key!r} cannot be written unquoted")
    check_comments(entry.comments)


def check_comments(comments: tuple[str, ...]) -> None:
    """Refuse a comment line that would not read back as a comment."""
    for comment in comments:
        if any(char in comment for char in _BREAKS):
            raise LvConfigError(f"comment {comment!r} contains a line break")
        if not comment.strip(_BLANKS).startswith((";", "#")):
            raise LvConfigError(f"comment {comment!r} does not start with ';' or '#'")


def check_config(config: Config) -> None:
    """Run every check over ``config`` before it is written."""
    for name, entries in config.sections.items():
        check_section(name)
        for key, entry in entries.items():
            check_key(key, entry)
    for name, comments in config.header_comments.items():
        if name not in config.sections:
            raise LvConfigError(f"header comments for missing section {name!r}")
        check_comments(comments)
    check_comments(config.trailing_comments)
