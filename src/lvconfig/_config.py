"""The ordered container returned by :func:`parse` and consumed by :func:`dump`."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._coerce import to_bool, to_float, to_int
from ._path import from_labview_path, to_labview_path
from ._validate import check_key, check_section

if TYPE_CHECKING:
    from ._layout import Layout


@dataclass(frozen=True)
class Entry:
    """One stored value: its decoded text, whether LabVIEW quotes it, its comments.

    Quoted entries are strings and paths, which LabVIEW escapes and wraps in double
    quotes. Unquoted entries are booleans and numbers, written as bare tokens.
    ``comments`` holds the verbatim comment lines that preceded the key on input, so a
    parsed file keeps its annotations through a dump.
    """

    value: str
    quoted: bool
    comments: tuple[str, ...] = ()


def _entry(value: str | bool | int | float) -> Entry:
    if isinstance(value, bool):
        return Entry("TRUE" if value else "FALSE", quoted=False)
    if isinstance(value, float) and not math.isfinite(value):
        # LabVIEW spells the special values Inf, -Inf and NaN, not Python's inf/nan.
        text = "NaN" if math.isnan(value) else ("Inf" if value > 0 else "-Inf")
        return Entry(text, quoted=False)
    if isinstance(value, (int, float)):
        return Entry(str(value), quoted=False)
    return Entry(value, quoted=True)


@dataclass
class Config:
    """Ordered sections of ordered key/value entries, preserving input order.

    ``header_comments`` maps a section name to the comment lines written above its
    header, and ``trailing_comments`` holds comment lines after the last key. Both let
    a parsed file keep its structure and annotations when dumped again.

    ``layout`` is the source formatting recorded by :func:`parse`. With it, a dump
    writes every untouched line back byte for byte. It takes no part in equality;
    set it to ``None`` to write the canonical form instead. Keys found before any
    section header live in the section named ``""``.
    """

    sections: dict[str, dict[str, Entry]] = field(default_factory=dict)
    header_comments: dict[str, tuple[str, ...]] = field(default_factory=dict)
    trailing_comments: tuple[str, ...] = ()
    layout: Layout | None = field(default=None, compare=False, repr=False)

    def section_names(self) -> list[str]:
        """Return the section names in the order they were added."""
        return list(self.sections)

    def keys(self, section: str) -> list[str]:
        """Return the keys of ``section`` in order, or an empty list if absent."""
        return list(self.sections.get(section, {}))

    def items(self, section: str) -> list[tuple[str, str]]:
        """Return ``(key, decoded value)`` pairs of ``section`` in order."""
        return [(key, entry.value) for key, entry in self.sections.get(section, {}).items()]

    def has(self, section: str, key: str) -> bool:
        """Report whether ``key`` exists under ``section``."""
        return key in self.sections.get(section, {})

    def set(self, section: str, key: str, value: str | bool | int | float) -> None:
        """Store ``value`` under ``section``/``key``, inferring its LabVIEW type.

        Raises :class:`LvConfigError` for a key or section name that would not read
        back as itself (one holding ``=`` or a line break, for example).
        A ``bool`` becomes ``TRUE``/``FALSE``, an ``int`` or ``float`` a bare number
        (``Inf``, ``-Inf`` and ``NaN`` spelled as LabVIEW does), and a ``str`` a quoted,
        escaped string. New sections keep insertion order. Replacing an existing key
        keeps the comment lines attached to it.
        """
        self._store(section, key, _entry(value))

    def set_path(self, section: str, key: str, path: str, *, windows: bool = True) -> None:
        """Store a native path under ``section``/``key`` in LabVIEW's stored form.

        ``windows`` picks the flavor of ``path``, as for :func:`to_labview_path`.
        """
        stored = to_labview_path(path, windows=windows)
        self._store(section, key, Entry(stored, quoted=True))

    def remove(self, section: str, key: str) -> bool:
        """Delete ``section``/``key`` if present; report whether it existed.

        The unnamed section ``""`` has no header line to keep it in a file, so it is
        dropped with its last key unless it carries header comments.
        """
        entries = self.sections.get(section)
        if entries is None or key not in entries:
            return False
        del entries[key]
        if section == "" and not entries and not self.header_comments.get(""):
            del self.sections[""]
        return True

    def remove_section(self, section: str) -> bool:
        """Delete ``section`` and its keys if present; report whether it existed."""
        if section not in self.sections:
            return False
        del self.sections[section]
        self.header_comments.pop(section, None)
        return True

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        """Return the decoded string value, or ``default`` when it is missing."""
        entry = self.sections.get(section, {}).get(key)
        return entry.value if entry is not None else default

    def get_str(self, section: str, key: str) -> str:
        """Return the decoded string value, raising ``KeyError`` when missing."""
        return self._require(section, key).value

    def get_bool(self, section: str, key: str) -> bool:
        """Return the value read as a LabVIEW boolean."""
        return to_bool(self._require(section, key).value)

    def get_int(self, section: str, key: str) -> int:
        """Return the value read as an integer."""
        return to_int(self._require(section, key).value)

    def get_float(self, section: str, key: str) -> float:
        """Return the value read as a floating-point number."""
        return to_float(self._require(section, key).value)

    def get_path(self, section: str, key: str, *, windows: bool = True) -> str:
        """Return the stored path decoded to a native path."""
        return from_labview_path(self._require(section, key).value, windows=windows)

    def to_dict(self) -> dict[str, dict[str, str]]:
        """Return the decoded sections and values as plain nested dictionaries."""
        return {
            name: {key: entry.value for key, entry in entries.items()}
            for name, entries in self.sections.items()
        }

    def _store(self, section: str, key: str, entry: Entry) -> None:
        check_section(section)
        previous = self.sections.get(section, {}).get(key)
        if previous is not None and previous.comments:
            entry = Entry(entry.value, entry.quoted, previous.comments)
        check_key(key, entry)
        self.sections.setdefault(section, {})[key] = entry

    def _require(self, section: str, key: str) -> Entry:
        try:
            return self.sections[section][key]
        except KeyError as exc:
            raise KeyError(f"{section!r}/{key!r}") from exc
