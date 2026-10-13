"""Checks that a config can be written as text that reads back as the same config.

A key holding ``=`` or a line break, a bare value LabVIEW would trim, unquote or cut at a
``;``, or a comment that does not start with ``;`` or ``#`` would be written fine but read
back as something else. These checks raise :class:`LvConfigError` instead, and
``TypeError`` for a config whose fields hold objects of the wrong type.
"""

from __future__ import annotations

from collections.abc import Set
from typing import TYPE_CHECKING

from ._check import need_str, short, type_name
from ._entry import Entry
from ._errors import LvConfigError

if TYPE_CHECKING:
    from ._config import Config

_BREAKS = ("\r", "\n")
_BLANKS = " \t"


def check_section(name: str) -> None:
    """Refuse a section name that cannot be written as one ``[name]`` line."""
    if any(char in name for char in _BREAKS):
        raise LvConfigError(f"section name {short(name)} contains a line break")


def check_key(key: str, entry: Entry, *, bare_checked: bool = True) -> None:
    """Refuse a key that would read back as a different key, a comment or a header."""
    if "=" in key or any(char in key for char in _BREAKS):
        raise LvConfigError(f"key {short(key)} contains '=' or a line break")
    if key != key.strip(_BLANKS):
        raise LvConfigError(f"key {short(key)} has leading or trailing whitespace")
    if key.startswith((";", "#")):
        raise LvConfigError(f"key {short(key)} starts with ';' or '#'")
    if key.startswith("[") and not entry.quoted and entry.value.endswith("]"):
        raise LvConfigError(f"key {short(key)} with a bare value ending in ']' reads as a header")
    if bare_checked and not entry.quoted and not is_bare_safe(entry.value):
        raise LvConfigError(f"bare value of {short(key)} cannot be written unquoted")
    check_comments(entry.comments)


def is_bare_safe(value: str) -> bool:
    """Report whether ``value`` reads back unchanged when written without quotes.

    LabVIEW trims spaces and tabs around a bare token, removes a pair of quotes around
    it, and treats a ``;`` in it as the start of a comment, so a bare value must have
    none of those.
    """
    if value != value.strip(_BLANKS) or ";" in value:
        return False
    return not (len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'")


def check_comments(comments: object) -> None:
    """Refuse a comment line that would not read back as a comment."""
    if not isinstance(comments, tuple):
        raise TypeError(f"comments must be a tuple, not {type_name(comments)}")
    for comment in comments:
        need_str("each comment", comment)
        if any(char in comment for char in _BREAKS):
            raise LvConfigError(f"comment {short(comment)} contains a line break")
        if not comment.strip(_BLANKS).startswith((";", "#")):
            raise LvConfigError(f"comment {short(comment)} does not start with ';' or '#'")


def check_config(config: Config, kept: Set[tuple[str, str]] = frozenset()) -> None:
    """Run every check over ``config`` before it is written.

    ``kept`` names the keys whose line is copied from the source unchanged; their bare
    value is already what the file holds, so it is not checked again.
    """
    if not isinstance(config.sections, dict):
        raise TypeError(f"sections must be a dict, not {type_name(config.sections)}")
    for name, entries in config.sections.items():
        check_section(need_str("section name", name))
        if not isinstance(entries, dict):
            raise TypeError(f"section {short(name)} must map keys to entries")
        for key, entry in entries.items():
            if not isinstance(entry, Entry):
                raise TypeError(f"entries must be Entry objects, not {type_name(entry)}")
            check_key(need_str("key", key), entry, bare_checked=(name, key) not in kept)
    if not isinstance(config.header_comments, dict):
        raise TypeError("header_comments must be a dict")
    for name, comments in config.header_comments.items():
        if need_str("section name", name) not in config.sections:
            raise LvConfigError(f"header comments for missing section {short(name)}")
        check_comments(comments)
    check_comments(config.trailing_comments)
