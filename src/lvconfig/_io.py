"""Read and write LabVIEW configuration files on disk.

LabVIEW on Windows writes these files with ``CRLF`` line endings, so :func:`save`
defaults to that. Non-displayable characters are hex-escaped in the content itself, so
the file body is plain text in the chosen encoding.
"""

from __future__ import annotations

import os

from ._config import Config
from ._dump import dump
from ._parse import parse

StrPath = str | os.PathLike[str]


def load(path: StrPath, *, encoding: str = "utf-8") -> Config:
    """Read a LabVIEW configuration file and parse it into a :class:`Config`."""
    with open(path, encoding=encoding) as handle:
        return parse(handle.read())


def save(
    config: Config,
    path: StrPath,
    *,
    encoding: str = "utf-8",
    line_ending: str = "\r\n",
) -> None:
    """Write ``config`` to ``path`` as LabVIEW configuration text.

    ``line_ending`` controls the terminator between lines and defaults to ``CRLF`` to
    match LabVIEW on Windows. Value content stays escaped, so no raw newline leaks in.
    """
    text = dump(config)
    if line_ending != "\n":
        text = text.replace("\n", line_ending)
    with open(path, "w", encoding=encoding, newline="") as handle:
        handle.write(text)
