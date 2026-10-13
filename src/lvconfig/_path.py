r"""Convert between native paths and LabVIEW's stored path form.

LabVIEW stores a path in a platform-neutral form that uses forward slashes and places
the drive letter after a leading slash, so ``C:\Temp\log.txt`` is written as
``/C/Temp/log.txt``. Reading that back on another platform, or with ``configparser``,
gives the wrong file.

A path that has no faithful counterpart is refused with :class:`LvPathError` instead
of being rewritten into a different path: a drive-relative ``C:file`` or bare ``C:``,
a rooted path with no drive (``\dir``), a UNC path without a share and a ``\\?\``
device path. The rules match the sibling ``lvpath`` library.
"""

from __future__ import annotations

import re

from ._check import need_bool, need_str, short
from ._errors import LvPathError

_WIN_DRIVE = re.compile(r"^([A-Za-z]):(.*)$", re.DOTALL)
_LV_DRIVE = re.compile(r"^/([A-Za-z])(?:/(.*))?$", re.DOTALL)
_LV_MALFORMED = re.compile(r"^/[A-Za-z][:\\]")
_DEVICE = ("\\\\?\\", "\\\\.\\")


def _check_unc(text: str, original: str) -> None:
    # ``text`` uses backslashes only; a UNC path needs both a server and a share.
    if text.startswith(_DEVICE):
        raise LvPathError(f"{short(original)} is a device path with no stored form")
    server, _, rest = text[2:].partition("\\")
    if not server or not rest.partition("\\")[0]:
        raise LvPathError(f"{short(original)} is not a \\\\server\\share UNC path")


def _windows_check(text: str, original: str) -> None:
    """Refuse a backslash-form Windows path that has no faithful stored form."""
    if text.startswith("\\\\"):
        _check_unc(text, original)
        return
    match = _WIN_DRIVE.match(text)
    if match and not match.group(2).startswith("\\"):
        raise LvPathError(f"{short(original)} is drive-relative and has no stored form")
    if text.startswith("\\"):
        raise LvPathError(f"{short(original)} is rooted without a drive or UNC share")


def _drive_path(drive: str, rest: str, original: str) -> str:
    # LabVIEW's Read Key (Path) drops empty and "." parts and resolves "..".
    parts: list[str] = []
    for part in rest.split("/"):
        if part in ("", "."):
            continue
        if part != "..":
            parts.append(part)
        elif parts:
            parts.pop()
        else:
            raise LvPathError(f"{short(original)} climbs above its drive root")
    return f"{drive}:\\" + "\\".join(parts)


def to_labview_path(path: str, *, windows: bool = True) -> str:
    r"""Encode a native path into LabVIEW's stored form.

    With ``windows`` true (the default), a Windows absolute path keeps its drive as
    ``/C/...`` and a bare drive root ``C:\`` becomes ``/C``. A UNC path keeps a
    leading double slash. A relative path has its backslashes turned into forward
    slashes, which is how LabVIEW stores it. Forward slashes are accepted as
    separators. With ``windows`` false the path is a POSIX path, which is already in
    stored form, and is returned unchanged.

    >>> to_labview_path(r"C:\Temp\log.txt"), to_labview_path(r"\\server\share\x")
    ('/C/Temp/log.txt', '//server/share/x')
    >>> to_labview_path(r"..\Builds\app.vi"), to_labview_path("/opt/rig", windows=False)
    ('../Builds/app.vi', '/opt/rig')

    Raises :class:`LvPathError` on Windows for a drive-relative, drive-less rooted
    (``\dir`` or ``/dir``, including a value already in stored form), incomplete
    UNC or device path, since any stored form would name a different file. Raises
    ``TypeError`` when ``path`` is not a ``str`` or ``windows`` not a ``bool``.
    """
    path = need_str("path", path)
    if not need_bool("windows", windows):
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
    r"""Decode a LabVIEW stored path to a native path, as LabVIEW reads it.

    With ``windows`` true, ``/C/Temp/log.txt`` becomes ``C:\Temp\log.txt`` and a
    leading ``//`` becomes a UNC ``\\`` prefix. In a drive path, empty and ``.`` parts
    are dropped and ``..`` goes up one level, as LabVIEW's Read Key (Path) does. A value
    already in native drive form (``C:\NI Installers``, which some NI files store) is
    accepted as is. With ``windows`` false the stored form already matches a POSIX path
    and is returned unchanged.

    >>> print(from_labview_path("/C/Temp/log.txt"))
    C:\Temp\log.txt
    >>> print(from_labview_path("/C/a//b/./c/../d/"))
    C:\a\b\d
    >>> print(from_labview_path("//server/share/dir"))
    \\server\share\dir

    Raises :class:`LvPathError` on Windows for a POSIX absolute path such as
    ``/usr/lib``, a malformed drive (``/C:/x``), a ``..`` above the drive root, a UNC
    path in backslash form (LabVIEW reads it as a different path) and the values
    :func:`to_labview_path` refuses. Raises ``TypeError`` for arguments of other types.
    """
    path = need_str("path", path)
    if not need_bool("windows", windows) or path == "":
        return path
    match = _LV_DRIVE.match(path)
    if match:
        return _drive_path(match.group(1), match.group(2) or "", path)
    if _LV_MALFORMED.match(path):
        raise LvPathError(f"{short(path)} has a malformed drive component, expected /C/...")
    if path.startswith("/") and not path.startswith(("//", "/\\")):
        raise LvPathError(f"{short(path)} is a POSIX absolute path with no Windows equivalent")
    text = path.replace("/", "\\")
    if text.startswith("\\\\") and not path.startswith("//"):
        raise LvPathError(f"{short(path)} is a UNC path in native form; store it as //server")
    _windows_check(text, path)
    return text
