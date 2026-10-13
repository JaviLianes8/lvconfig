"""The ordered container returned by :func:`parse` and consumed by :func:`dump`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._check import need_str, short
from ._coerce import to_bool, to_float, to_int
from ._entry import Entry, Value, make_entry
from ._path import from_labview_path, to_labview_path
from ._validate import check_key, check_section

if TYPE_CHECKING:
    from ._layout import Layout


@dataclass
class Config:
    """Ordered sections of ordered key/value entries, preserving input order.

    ``header_comments`` maps a section name to the comment lines written above its
    header, and ``trailing_comments`` holds comment lines after the last key. Both let
    a parsed file keep its structure and annotations when dumped again.

    ``layout`` is the source formatting recorded by :func:`parse`. With it, a dump
    writes every untouched line back byte for byte. It takes no part in equality;
    set it to ``None`` to write the canonical form instead. Keys found before any
    section header live in the section named ``""``. Section and key names are
    matched exactly, case included.

    >>> config = Config()
    >>> config.set("Rig", "retries", 3)
    >>> config.sections
    {'Rig': {'retries': Entry(value='3', quoted=False, comments=())}}

    Every method raises ``TypeError`` for a section or key name that is not a ``str``.
    """

    sections: dict[str, dict[str, Entry]] = field(default_factory=dict)
    header_comments: dict[str, tuple[str, ...]] = field(default_factory=dict)
    trailing_comments: tuple[str, ...] = ()
    layout: Layout | None = field(default=None, compare=False, repr=False)

    def section_names(self) -> list[str]:
        """Return the section names in the order they were added.

        >>> config = Config(); config.set("B", "x", 1); config.set("A", "y", 2)
        >>> config.section_names()
        ['B', 'A']
        """
        return list(self.sections)

    def keys(self, section: str) -> list[str]:
        """Return the keys of ``section`` in order, or an empty list if absent.

        >>> config = Config(); config.set("A", "x", 1); config.set("A", "y", 2)
        >>> config.keys("A"), config.keys("missing")
        (['x', 'y'], [])
        """
        return list(self.sections.get(need_str("section", section), {}))

    def items(self, section: str) -> list[tuple[str, str]]:
        """Return ``(key, decoded value)`` pairs of ``section`` in order.

        >>> config = Config(); config.set("A", "name", "Rig"); config.set("A", "on", True)
        >>> config.items("A")
        [('name', 'Rig'), ('on', 'TRUE')]
        """
        entries = self.sections.get(need_str("section", section), {})
        return [(key, entry.value) for key, entry in entries.items()]

    def has(self, section: str, key: str) -> bool:
        """Report whether ``key`` exists under ``section``.

        >>> config = Config(); config.set("A", "x", 1)
        >>> config.has("A", "x"), config.has("A", "X")
        (True, False)
        """
        return need_str("key", key) in self.sections.get(need_str("section", section), {})

    def set(self, section: str, key: str, value: Value) -> None:
        """Store ``value`` under ``section``/``key``, inferring its LabVIEW type.

        A ``bool`` becomes ``TRUE``/``FALSE``, an ``int`` or ``float`` a bare number
        (``Inf``, ``-Inf`` and ``NaN`` spelled as LabVIEW does), and a ``str`` a quoted
        string. New sections keep insertion order. Replacing an existing key keeps the
        comment lines attached to it.

        >>> config = Config(); config.set("A", "gain", 2.5); config.set("A", "x", "1")
        >>> config.sections["A"]["gain"], config.sections["A"]["x"].quoted
        (Entry(value='2.5', quoted=False, comments=()), True)

        Raises :class:`LvConfigError` for a key or section name that would not read back
        as itself (one holding ``=`` or a line break, for example), and ``TypeError`` for
        a value of another type.
        """
        self._store(section, key, make_entry(value))

    def set_path(self, section: str, key: str, path: str, *, windows: bool = True) -> None:
        r"""Store a native path under ``section``/``key`` in LabVIEW's stored form.

        ``windows`` picks the flavor of ``path``, as for :func:`to_labview_path`.

        >>> config = Config(); config.set_path("Paths", "log", r"C:\Temp\log.txt")
        >>> config.get_str("Paths", "log")
        '/C/Temp/log.txt'

        Raises :class:`LvPathError` for a path with no faithful stored form.
        """
        need_str("section", section)
        need_str("key", key)
        stored = to_labview_path(path, windows=windows)
        self._store(section, key, Entry(stored, quoted=True))

    def remove(self, section: str, key: str) -> bool:
        """Delete ``section``/``key`` if present; report whether it existed.

        The unnamed section ``""`` has no header line to keep it in a file, so it is
        dropped with its last key unless it carries header comments.

        >>> config = Config(); config.set("A", "x", 1)
        >>> config.remove("A", "x"), config.remove("A", "x"), config.section_names()
        (True, False, ['A'])
        """
        entries = self.sections.get(need_str("section", section))
        if entries is None or need_str("key", key) not in entries:
            return False
        del entries[key]
        if section == "" and not entries and not self.header_comments.get(""):
            del self.sections[""]
        return True

    def remove_section(self, section: str) -> bool:
        """Delete ``section``, its keys and its header comments; report whether it existed.

        >>> config = Config(); config.set("A", "x", 1)
        >>> config.remove_section("A"), config.remove_section("A")
        (True, False)
        """
        if need_str("section", section) not in self.sections:
            return False
        del self.sections[section]
        self.header_comments.pop(section, None)
        return True

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        """Return the decoded string value, or ``default`` when it is missing.

        >>> config = Config(); config.set("A", "x", "text")
        >>> config.get("A", "x"), config.get("A", "y"), config.get("A", "y", "fallback")
        ('text', None, 'fallback')
        """
        entry = self.sections.get(need_str("section", section), {}).get(need_str("key", key))
        return entry.value if entry is not None else default

    def get_str(self, section: str, key: str) -> str:
        """Return the decoded string value; ``KeyError`` when it is missing.

        >>> config = Config(); config.set("A", "x", "text")
        >>> config.get_str("A", "x")
        'text'
        """
        return self._require(section, key).value

    def get_bool(self, section: str, key: str) -> bool:
        """Return the value read as a LabVIEW boolean, as :func:`to_bool` reads it.

        >>> config = Config(); config.set("A", "on", True)
        >>> config.get_bool("A", "on")
        True
        """
        return to_bool(self._require(section, key).value)

    def get_int(self, section: str, key: str) -> int:
        """Return the value read as an integer, as :func:`to_int` reads it.

        >>> config = Config(); config.set("A", "n", 42)
        >>> config.get_int("A", "n")
        42
        """
        return to_int(self._require(section, key).value)

    def get_float(self, section: str, key: str) -> float:
        """Return the value read as a number, as :func:`to_float` reads it.

        >>> config = Config(); config.set("A", "gain", 0.5)
        >>> config.get_float("A", "gain")
        0.5
        """
        return to_float(self._require(section, key).value)

    def get_path(self, section: str, key: str, *, windows: bool = True) -> str:
        """Return the stored path decoded to a native path, as :func:`from_labview_path`.

        >>> config = Config(); config.set("Paths", "log", "/C/Temp/log.txt")
        >>> print(config.get_path("Paths", "log"))
        C:\\Temp\\log.txt
        """
        return from_labview_path(self._require(section, key).value, windows=windows)

    def to_dict(self) -> dict[str, dict[str, str]]:
        """Return the decoded sections and values as plain nested dictionaries.

        >>> config = Config(); config.set("A", "x", 1)
        >>> config.to_dict()
        {'A': {'x': '1'}}
        """
        return {
            name: {key: entry.value for key, entry in entries.items()}
            for name, entries in self.sections.items()
        }

    def _store(self, section: str, key: str, entry: Entry) -> None:
        check_section(need_str("section", section))
        need_str("key", key)
        previous = self.sections.get(section, {}).get(key)
        if previous is not None and previous.comments:
            entry = Entry(entry.value, entry.quoted, previous.comments)
        check_key(key, entry)
        self.sections.setdefault(section, {})[key] = entry

    def _require(self, section: str, key: str) -> Entry:
        entry = self.sections.get(need_str("section", section), {}).get(need_str("key", key))
        if entry is None:
            raise KeyError(f"no key {short(key)} in section {short(section)}")
        return entry
