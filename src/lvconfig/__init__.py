"""Typed reader and writer for LabVIEW configuration files.

LabVIEW's "Configuration File" format looks like an INI file but follows its own rules:
``\\XX`` hex escapes for control characters, doubled backslashes, quoted-string
whitespace, paths stored as ``/C/...``, and ``TRUE``/``FALSE`` booleans. Python's
``configparser`` honours none of these and corrupts such files. This package reads and
writes them faithfully, and coerces values to the Python types they stand for.
"""

from __future__ import annotations

from ._coerce import to_bool, to_float, to_int
from ._config import Config, Entry
from ._dump import dump
from ._errors import LvConfigError, LvParseError
from ._escape import escape, unescape
from ._io import load, save
from ._parse import parse
from ._path import from_labview_path, to_labview_path

__version__ = "0.2.0"

__all__ = [
    "Config",
    "Entry",
    "LvConfigError",
    "LvParseError",
    "dump",
    "escape",
    "from_labview_path",
    "load",
    "parse",
    "save",
    "to_bool",
    "to_float",
    "to_int",
    "to_labview_path",
    "unescape",
]
