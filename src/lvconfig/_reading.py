"""Typed reading of a :class:`Config`'s values, shared through a base class."""

from __future__ import annotations

from typing import overload

from ._check import need_str, short
from ._coerce import to_bool, to_float, to_int
from ._entry import Entry
from ._path import from_labview_path
from ._stored import stored


def _typed(entry: Entry) -> str:
    # LabVIEW's typed Read Key VIs read the stored text, up to a bare ';' comment.
    text = stored(entry)
    return text if entry.quoted else text.partition(";")[0]


class Reading:
    """The read side of :class:`Config`: every getter decodes the stored text."""

    sections: dict[str, dict[str, Entry]]

    @overload
    def get(self, section: str, key: str) -> str | None: ...

    @overload
    def get(self, section: str, key: str, default: str) -> str: ...

    @overload
    def get(self, section: str, key: str, default: None) -> str | None: ...

    def get(self, section: str, key: str, default: str | None = None) -> str | None:
        """Return the decoded string value, or ``default`` when it is missing.

        With a ``str`` default the result is typed ``str``.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "x", "text")
        >>> config.get("A", "x"), config.get("A", "y"), config.get("A", "y", "fallback")
        ('text', None, 'fallback')
        """
        if default is not None:
            need_str("default", default)
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
        return to_bool(_typed(self._require(section, key)))

    def get_int(self, section: str, key: str) -> int:
        """Return the value read as an integer, as :func:`to_int` reads it.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "n", 42)
        >>> config.get_int("A", "n")
        42
        """
        return to_int(_typed(self._require(section, key)))

    def get_float(self, section: str, key: str) -> float:
        """Return the value read as a number, as :func:`to_float` reads it.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("A", "gain", 0.5)
        >>> config.get_float("A", "gain")
        0.5
        """
        return to_float(_typed(self._require(section, key)))

    def get_path(self, section: str, key: str, *, windows: bool = True) -> str:
        """Return the stored path decoded to a native path, as :func:`from_labview_path`.

        >>> from lvconfig import Config
        >>> config = Config(); config.set("Paths", "log", "/C/Temp/log.txt")
        >>> print(config.get_path("Paths", "log"))
        C:\\Temp\\log.txt

        LabVIEW's Read Key (Path) does not decode ``\\XX`` codes: every backslash in the
        stored text is a separator. So on Windows the stored text, not its decoded string,
        is what is resolved: ``/C/\\09x`` reads as ``C:\\09x``.
        """
        entry = self._require(section, key)
        return from_labview_path(stored(entry) if windows else entry.value, windows=windows)

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
