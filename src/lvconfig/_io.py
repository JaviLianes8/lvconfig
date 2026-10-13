"""Read and write LabVIEW configuration files on disk.

:func:`load` keeps the file's exact line endings, so a loaded file saved again is
byte-identical until a value changes. A config built in code is written with the
``CRLF`` line endings LabVIEW uses on Windows. Non-displayable characters are
hex-escaped in the content itself, so the file body is plain text in the chosen
encoding.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile

from ._check import need_str, short, type_name
from ._config import Config
from ._dump import dump
from ._parse import parse

StrPath = str | os.PathLike[str]

_ENDINGS = ("\r\n", "\n", "\r")
_EOL = re.compile(r"\r\n|\n|\r")


def load(path: StrPath, *, encoding: str = "utf-8") -> Config:
    r"""Read a LabVIEW configuration file and parse it into a :class:`Config`.

    The text is read without newline translation, so the recorded layout keeps the
    file's own ``CRLF`` or ``LF`` endings and a missing final newline. LabVIEW writes
    files in the system code page; pass that ``encoding`` (``"cp1252"`` on a western
    Windows system) for a file holding text beyond ASCII.

    Raises ``OSError`` when the file cannot be read, ``UnicodeDecodeError`` when it is
    not in ``encoding``, ``LookupError`` for an unknown encoding and
    :class:`LvParseError` for a line that is not a section, key or comment.

    >>> import pathlib, tempfile
    >>> path = pathlib.Path(tempfile.mkdtemp(), "rig.ini")
    >>> _ = path.write_bytes(b"[Rig]\r\nretries = 3")
    >>> load(path).get_int("Rig", "retries")
    3
    >>> import shutil; shutil.rmtree(path.parent)
    """
    need_str("encoding", encoding)
    with open(need_path(path), encoding=encoding, newline="") as handle:
        return parse(handle.read())


def save(
    config: Config,
    path: StrPath,
    *,
    encoding: str = "utf-8",
    line_ending: str | None = None,
) -> None:
    r"""Write ``config`` to ``path`` as LabVIEW configuration text.

    With ``line_ending`` left as ``None``, a loaded or parsed config keeps the line
    endings it was read with and a config built in code gets ``CRLF``. Passing
    ``"\r\n"`` or ``"\n"`` forces that terminator on every line. Value content stays
    escaped, so no raw newline leaks in. The text is rendered before the file is
    opened, so a config :func:`dump` refuses leaves the file untouched.

    Raises :class:`LvConfigError` for a config :func:`dump` refuses, ``ValueError`` for
    a ``line_ending`` other than ``None``, CRLF, LF or CR, and ``OSError``,
    ``UnicodeEncodeError`` or ``LookupError`` from writing the file.

    >>> import pathlib, tempfile
    >>> path = pathlib.Path(tempfile.mkdtemp(), "rig.ini")
    >>> config = Config()
    >>> config.set("Rig", "retries", 3)
    >>> save(config, path)
    >>> path.read_bytes()
    b'[Rig]\r\nretries = 3'
    >>> import shutil; shutil.rmtree(path.parent)
    """
    need_path(path)
    need_str("encoding", encoding)
    if line_ending is not None and need_str("line_ending", line_ending) not in _ENDINGS:
        raise ValueError(f"line_ending must be CRLF, LF or CR, not {short(line_ending)}")
    text = dump(config)
    if line_ending is None and config.layout is None:
        line_ending = "\r\n"
    if line_ending is not None:
        text = _EOL.sub(line_ending, text)
    write_text(path, text, encoding)


def need_path(path: object) -> StrPath:
    """Return ``path`` if it is a ``str`` or a text ``os.PathLike``, else ``TypeError``.

    A bare ``int`` would be taken by ``open`` as a file descriptor and closed afterwards.
    """
    if isinstance(path, str) or (
        isinstance(path, os.PathLike) and isinstance(os.fspath(path), str)
    ):
        return path
    raise TypeError(f"path must be a str or os.PathLike, not {type_name(path)}")


def write_text(path: StrPath, text: str, encoding: str) -> None:
    """Write ``text`` to ``path`` through a temporary file in the same folder.

    The text is encoded first, then written to the temporary file, which then replaces
    the target. An encoding error, a full disk or a locked target raises with the old
    file left as it was.
    """
    data = text.encode(encoding)
    target = os.fspath(need_path(path))
    folder = os.path.dirname(os.path.abspath(target))
    handle, temporary = tempfile.mkstemp(prefix=".lvconfig-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(temporary)
        raise
