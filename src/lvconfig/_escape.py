"""LabVIEW string escaping: ``\\XX`` codes for control characters and doubled backslashes.

The rules are the ones LabVIEW 2026's Configuration File VIs follow, as captured from
LabVIEW itself (``tests/fixtures/labview2026``). On write, a backslash is doubled and
every control character below 0x20 except tab becomes a backslash and two upper-case hex
digits (``\\0D`` is a carriage return). Tab, the double quote, DEL and every character
from 0x80 up are written as they are. On read, ``\\\\`` is one backslash and only
``\\00`` to ``\\1F`` in upper case are codes; any other backslash is a literal one.
Python's ``configparser`` knows none of this, so it corrupts any value that holds a code.
"""

from __future__ import annotations

from ._check import need_bool, need_str

_FIRST = "01"
_SECOND = "0123456789ABCDEF"


def escape(value: str, *, raw: bool = False) -> str:
    r"""Encode a string the way LabVIEW writes it into a configuration file.

    A backslash is doubled and every control character below 0x20 other than tab
    becomes ``\XX`` with two upper-case hex digits. Everything else, including tab,
    ``"`` and characters from 0x7F up, is kept. With ``raw`` the string is returned
    unchanged, like LabVIEW's "write raw string?" mode.

    >>> print(escape("line 1\nline 2"))
    line 1\0Aline 2
    >>> print(escape('C:\\Temp "quoted"'))
    C:\\Temp "quoted"
    >>> escape("a\nb", raw=True)
    'a\nb'

    Raises ``TypeError`` when ``value`` is not a ``str`` or ``raw`` not a ``bool``.
    """
    text = need_str("value", value)
    if need_bool("raw", raw):
        return text
    out: list[str] = []
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif char < " " and char != "\t":
            out.append(f"\\{ord(char):02X}")
        else:
            out.append(char)
    return "".join(out)


def unescape(value: str) -> str:
    r"""Decode a stored string the way LabVIEW reads it.

    ``\\`` becomes one backslash and ``\00`` to ``\1F`` (upper-case hex) become the
    control character they name. Any other backslash, such as the one in ``\22``,
    ``\7F`` or ``\0a``, is kept as a literal backslash, as LabVIEW keeps it.

    >>> unescape(r"Rig\09A")
    'Rig\tA'
    >>> print(unescape(r"C:\\Temp \22 \0a"))
    C:\Temp \22 \0a

    Raises ``TypeError`` when ``value`` is not a ``str``.
    """
    text = need_str("value", value)
    out: list[str] = []
    i = 0
    length = len(text)
    while i < length:
        char = text[i]
        if char != "\\":
            out.append(char)
            i += 1
        elif i + 1 < length and text[i + 1] == "\\":
            out.append("\\")
            i += 2
        elif i + 2 < length and text[i + 1] in _FIRST and text[i + 2] in _SECOND:
            out.append(chr(int(text[i + 1 : i + 3], 16)))
            i += 3
        else:
            out.append("\\")
            i += 1
    return "".join(out)
