"""The ordered container returned by :func:`parse` and consumed by :func:`dump`."""

from __future__ import annotations

from dataclasses import dataclass, field

from ._coerce import to_bool, to_float, to_int
from ._path import from_labview_path, to_labview_path


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
    if isinstance(value, (int, float)):
        return Entry(str(value), quoted=False)
    return Entry(value, quoted=True)


@dataclass
class Config:
    """Ordered sections of ordered key/value entries, preserving input order.

    ``header_comments`` maps a section name to the comment lines written above its
    header, and ``trailing_comments`` holds comment lines after the last key. Both let
    a parsed file keep its structure and annotations when dumped again.
    """

    sections: dict[str, dict[str, Entry]] = field(default_factory=dict)
    header_comments: dict[str, tuple[str, ...]] = field(default_factory=dict)
    trailing_comments: tuple[str, ...] = ()

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

        A ``bool`` becomes ``TRUE``/``FALSE``, an ``int`` or ``float`` a bare number,
        and a ``str`` a quoted, escaped string. New sections keep insertion order.
        """
        self.sections.setdefault(section, {})[key] = _entry(value)

    def set_path(self, section: str, key: str, path: str) -> None:
        """Store a native path under ``section``/``key`` in LabVIEW's stored form."""
        self.sections.setdefault(section, {})[key] = Entry(to_labview_path(path), quoted=True)

    def remove(self, section: str, key: str) -> bool:
        """Delete ``section``/``key`` if present; report whether it existed."""
        entries = self.sections.get(section)
        if entries is None or key not in entries:
            return False
        del entries[key]
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

    def _require(self, section: str, key: str) -> Entry:
        try:
            return self.sections[section][key]
        except KeyError as exc:
            raise KeyError(f"{section!r}/{key!r}") from exc
