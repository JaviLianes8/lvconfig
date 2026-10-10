"""LabVIEW string escaping: ``\\XX`` hex codes and doubled backslashes.

LabVIEW stores control and non-displayable characters in configuration files as a
backslash followed by two uppercase hexadecimal digits (``\\0D`` is a carriage
return), and a literal backslash as ``\\\\``. Python's ``configparser`` knows none of
this, so it corrupts any value that carries such a code.
"""

from __future__ import annotations

_HEX = "0123456789abcdefABCDEF"


def escape(value: str, *, raw: bool = False) -> str:
    """Encode a decoded string into LabVIEW's escaped form.

    Backslashes double, the double quote and control characters (code point below
    0x20 or 0x7F) become ``\\XX`` with two uppercase hex digits. With ``raw`` the
    string is returned unchanged, matching LabVIEW's raw write mode.
    """
    if raw:
        return value
    out: list[str] = []
    for char in value:
        code = ord(char)
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append("\\22")
        elif code < 0x20 or code == 0x7F:
            out.append(f"\\{code:02X}")
        else:
            out.append(char)
    return "".join(out)


def unescape(value: str) -> str:
    """Decode a LabVIEW escaped string back to its literal characters.

    ``\\\\`` becomes one backslash and ``\\XX`` (two hex digits, any case) becomes
    the matching character. An unrecognised escape keeps its backslash verbatim, so
    no information is lost on input LabVIEW would not itself have written.
    """
    out: list[str] = []
    i = 0
    length = len(value)
    while i < length:
        char = value[i]
        if char != "\\":
            out.append(char)
            i += 1
            continue
        if i + 1 < length and value[i + 1] == "\\":
            out.append("\\")
            i += 2
        elif i + 2 < length and value[i + 1] in _HEX and value[i + 2] in _HEX:
            out.append(chr(int(value[i + 1 : i + 3], 16)))
            i += 3
        else:
            out.append("\\")
            i += 1
    return "".join(out)
