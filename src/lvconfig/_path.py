"""Convert between native paths and LabVIEW's stored path form.

LabVIEW stores a path in a platform-neutral form that uses forward slashes and places
the drive letter after a leading slash, so ``C:\\Temp\\log.txt`` is written as
``/C/Temp/log.txt``. Reading that back on another platform, or with ``configparser``,
gives the wrong file.
"""

from __future__ import annotations

import re

_WIN_DRIVE = re.compile(r"^([A-Za-z]):[\\/]?(.*)$", re.DOTALL)
_LV_DRIVE = re.compile(r"^/([A-Za-z])(?:/(.*))?$", re.DOTALL)


def to_labview_path(path: str) -> str:
    """Encode a native path into LabVIEW's stored form.

    A Windows absolute path keeps its drive as ``/C/...``. A UNC path keeps a
    leading double slash. Any other path is returned with backslashes turned into
    forward slashes, which already matches how LabVIEW stores relative paths.
    """
    if path.startswith("\\\\"):
        return "//" + path[2:].replace("\\", "/")
    match = _WIN_DRIVE.match(path)
    if match:
        drive, rest = match.group(1), match.group(2).replace("\\", "/")
        return f"/{drive}/{rest}" if rest else f"/{drive}"
    return path.replace("\\", "/")


def from_labview_path(path: str, *, windows: bool = True) -> str:
    """Decode a LabVIEW stored path to a native path.

    With ``windows`` true, ``/C/Temp/log.txt`` becomes ``C:\\Temp\\log.txt`` and a
    leading ``//`` becomes a UNC ``\\\\`` prefix. With ``windows`` false the stored
    form already matches a POSIX path and is returned unchanged.
    """
    if not windows:
        return path
    if path.startswith("//"):
        return "\\\\" + path[2:].replace("/", "\\")
    match = _LV_DRIVE.match(path)
    if match:
        drive, rest = match.group(1), match.group(2)
        return f"{drive}:\\{rest.replace('/', chr(92))}" if rest else f"{drive}:\\"
    return path.replace("/", "\\")
