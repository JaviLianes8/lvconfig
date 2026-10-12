"""Convert between native paths and LabVIEW's stored path form.

LabVIEW stores a path in a platform-neutral form that uses forward slashes and places
the drive letter after a leading slash, so ``C:\\Temp\\log.txt`` is written as
``/C/Temp/log.txt``. Reading that back on another platform, or with ``configparser``,
gives the wrong file.

A path that has no faithful counterpart is refused with :class:`LvPathError` instead
of being rewritten into a different path: a drive-relative ``C:file`` or bare ``C:``,
a rooted path with no drive (``\\dir``), a UNC path without a share and a ``\\\\?\\``
device path. The rules match the sibling ``lvpath`` library.
"""

from __future__ import annotations

import re

from ._errors import LvPathError

_WIN_DRIVE = re.compile(r"^([A-Za-z]):(.*)$", re.DOTALL)
_LV_DRIVE = re.compile(r"^/([A-Za-z])(?:/(.*))?$", re.DOTALL)
_LV_MALFORMED = re.compile(r"^/[A-Za-z][:\\]")
_DEVICE = ("\\\\?\\", "\\\\.\\")


def _check_unc(text: str, original: str) -> None:
    # ``text`` uses backslashes only; a UNC path needs both a server and a share.
    if text.startswith(_DEVICE):
        raise LvPathError(f"{original!r} is a device path with no stored form")
    server, _, rest = text[2:].partition("\\")
    if not server or not rest.partition("\\")[0]:
        raise LvPathError(f"{original!r} is not a \\\\server\\share UNC path")


def _windows_check(text: str, original: str) -> None:
    """Refuse a backslash-form Windows path that has no faithful stored form."""
    if text.startswith("\\\\"):
        _check_unc(text, original)
        return
    match = _WIN_DRIVE.match(text)
    if match and not match.group(2).startswith("\\"):
        raise LvPathError(f"{original!r} is drive-relative and has no stored form")
    if text.startswith("\\"):
        raise LvPathError(f"{original!r} is rooted without a drive or UNC share")


def to_labview_path(path: str, *, windows: bool = True) -> str:
    """Encode a native path into LabVIEW's stored form.

    With ``windows`` true (the default), a Windows absolute path keeps its drive as
    ``/C/...`` and a bare drive root ``C:\\`` becomes ``/C``. A UNC path keeps a
    leading double slash. A relative path has its backslashes turned into forward
    slashes, which is how LabVIEW stores it. Forward slashes are accepted as
    separators. With ``windows`` false the path is a POSIX path, which is already in
    stored form, and is returned unchanged.

    Raises :class:`LvPathError` on Windows for a drive-relative, drive-less rooted
    (``\\dir`` or ``/dir``, including a value already in stored form), incomplete
    UNC or device path, since any stored form would name a different file.
    """
    if not windows:
        return path
    text = path.replace("/", "\\")
    _windows_check(text, path)
    if text.startswith("\\\\"):
        return "/" + text[1:].replace("\\", "/")
    match = _WIN_DRIVE.match(text)
    if match:
        drive, rest = match.group(1), match.group(2)[1:].replace("\\", "/")
        return f"/{drive}/{rest}" if rest else f"/{drive}"
    return text.replace("\\", "/")


def from_labview_path(path: str, *, windows: bool = True) -> str:
    """Decode a LabVIEW stored path to a native path.

    With ``windows`` true, ``/C/Temp/log.txt`` becomes ``C:\\Temp\\log.txt`` and a
    leading ``//`` becomes a UNC ``\\\\`` prefix. A value already in native Windows
    form (``C:\\NI Installers``, which some NI files store) is accepted as is. With
    ``windows`` false the stored form already matches a POSIX path and is returned
    unchanged.

    Raises :class:`LvPathError` on Windows for a POSIX absolute path such as
    ``/usr/lib``, a malformed drive (``/C:/x``) and the values
    :func:`to_labview_path` refuses.
    """
    if not windows or path == "":
        return path
    match = _LV_DRIVE.match(path)
    if match:
        drive, rest = match.group(1), match.group(2)
        return f"{drive}:\\{rest.replace('/', chr(92))}" if rest else f"{drive}:\\"
    if _LV_MALFORMED.match(path):
        raise LvPathError(f"{path!r} has a malformed drive component, expected /C/...")
    if path.startswith("/") and not path.startswith(("//", "/\\")):
        raise LvPathError(f"{path!r} is a POSIX absolute path with no Windows equivalent")
    text = path.replace("/", "\\")
    _windows_check(text, path)
    return text
