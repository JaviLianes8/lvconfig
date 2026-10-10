"""Exceptions raised across the package."""

from __future__ import annotations


class LvConfigError(Exception):
    """Base class for every error this library raises."""


class LvParseError(LvConfigError):
    """A configuration text could not be parsed into sections and keys."""

    def __init__(self, message: str, line: int) -> None:
        # The line number lets a caller point a user at the offending input.
        super().__init__(f"line {line}: {message}")
        self.line = line
