"""Exceptions raised across the package."""

from __future__ import annotations


class LvConfigError(Exception):
    """Base class for the errors specific to this library.

    Raised when text is not the type asked for, or when a config would not read back as
    written. Wrong argument types raise ``TypeError`` and file access raises ``OSError``
    as usual, not this.

    >>> from lvconfig import to_int
    >>> try:
    ...     to_int("twelve")
    ... except LvConfigError as error:
    ...     print(error)
    not an integer: 'twelve'
    """


class LvPathError(LvConfigError, ValueError):
    r"""A path has no faithful equivalent in the requested form.

    Raised instead of silently rewriting a value into a path that names a different
    file, for example a drive-relative ``C:file``. It is also a ``ValueError``.

    >>> from lvconfig import to_labview_path
    >>> try:
    ...     to_labview_path(r"\Windows")
    ... except LvPathError as error:
    ...     print(error)
    '\\Windows' is rooted without a drive or UNC share
    """


class LvParseError(LvConfigError):
    """A configuration text could not be parsed into sections and keys.

    ``line`` is the 1-based number of the offending line.

    >>> from lvconfig import parse
    >>> try:
    ...     parse("[A]\\nnot a key line")
    ... except LvParseError as error:
    ...     print(error.line, error)
    2 line 2: expected a key=value pair: 'not a key line'
    """

    def __init__(self, message: str, line: int) -> None:
        # The line number lets a caller point a user at the offending input.
        super().__init__(f"line {line}: {message}")
        self.line = line
        self._message = message

    def __reduce__(self) -> tuple[type[LvParseError], tuple[str, int]]:
        # Rebuild from the constructor's own arguments, so copy and pickle work.
        return (type(self), (self._message, self.line))
