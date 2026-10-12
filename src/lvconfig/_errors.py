"""Exceptions raised across the package."""

from __future__ import annotations


class LvConfigError(Exception):
    """Base class for every error this library raises."""


class LvPathError(LvConfigError, ValueError):
    """A path has no faithful equivalent in the requested form.

    Raised instead of silently rewriting a value into a path that names a different
    file, for example a drive-relative ``C:file``.
    """


class LvParseError(LvConfigError):
    """A configuration text could not be parsed into sections and keys."""

    def __init__(self, message: str, line: int) -> None:
        # The line number lets a caller point a user at the offending input.
        super().__init__(f"line {line}: {message}")
        self.line = line
