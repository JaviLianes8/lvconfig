"""Typed reading of a :class:`Config`'s values, shared through a base class."""

from __future__ import annotations

from ._check import need_str, short
from ._coerce import to_bool, to_float, to_int
from ._entry import Entry
from ._path import from_labview_path


class Reading:
    """The read side of :class:`Config`: every getter decodes the stored text."""

    sections: dict[str, dict[str, Entry]]

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        """Return the decoded string value, or ``default`` when it is missing.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "x", "text")
        >>> config.get("A", "x"), config.get("A", "y"), config.get("A", "y", "fallback")
        ('text', None, 'fallback')
        """
        entry = self.sections.get(need_str("section", section), {}).get(need_str("key", key))
        return entry.value if entry is not None else default

    def get_str(self, section: str, key: str) -> str:
        """Return the decoded string value; ``KeyError`` when it is missing.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "x", "text")
        >>> config.get_str("A", "x")
        'text'
        """
        return self._require(section, key).value

    def get_bool(self, section: str, key: str) -> bool:
        """Return the value read as a LabVIEW boolean, as :func:`to_bool` reads it.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "on", True)
        >>> config.get_bool("A", "on")
        True
        """
        return to_bool(self._require(section, key).value)

    def get_int(self, section: str, key: str) -> int:
        """Return the value read as an integer, as :func:`to_int` reads it.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "n", 42)
        >>> config.get_int("A", "n")
        42
        """
        return to_int(self._require(section, key).value)

    def get_float(self, section: str, key: str) -> float:
        """Return the value read as a number, as :func:`to_float` reads it.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "gain", 0.5)
        >>> config.get_float("A", "gain")
        0.5
        """
        return to_float(self._require(section, key).value)

    def get_path(self, section: str, key: str, *, windows: bool = True) -> str:
        """Return the stored path decoded to a native path, as :func:`from_labview_path`.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("Paths", "log", "/C/Temp/log.txt")
        >>> print(config.get_path("Paths", "log"))
        C:\\Temp\\log.txt
        """
        return from_labview_path(self._require(section, key).value, windows=windows)

    def to_dict(self) -> dict[str, dict[str, str]]:
        """Return the decoded sections and values as plain nested dictionaries.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "x", 1)
        >>> config.to_dict()
        {'A': {'x': '1'}}
        """
        return {
            name: {key: entry.value for key, entry in entries.items()}
            for name, entries in self.sections.items()
        }

    def _require(self, section: str, key: str) -> Entry:
        entry = self.sections.get(need_str("section", section), {}).get(need_str("key", key))
        if entry is None:
            raise KeyError(f"no key {short(key)} in section {short(section)}")
        return entry
