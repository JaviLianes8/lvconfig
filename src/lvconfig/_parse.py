"""Parse LabVIEW configuration text into an ordered :class:`Config`."""

from __future__ import annotations

from ._config import Config, Entry
from ._errors import LvParseError
from ._escape import unescape


def _value(raw: str, comments: tuple[str, ...]) -> Entry:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        # Quoted strings and paths: the quotes come off and escapes are decoded.
        return Entry(unescape(text[1:-1]), quoted=True, comments=comments)
    return Entry(text, quoted=False, comments=comments)


def parse(text: str) -> Config:
    """Parse configuration text into ordered sections and keys.

    Sections are ``[name]`` headers, keys are ``key = value`` lines, and whole-line
    comments start with ``;``. Comment lines are kept and attached to the section or key
    that follows them, so a dump reproduces them. Repeated sections merge in order. A key
    before any section, or a non-blank line that is none of the above, raises
    :class:`LvParseError`.
    """
    config = Config()
    current: dict[str, Entry] | None = None
    pending: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(";"):
            pending.append(stripped)
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            name = stripped[1:-1]
            current = config.sections.setdefault(name, {})
            if pending:
                prior = config.header_comments.get(name, ())
                config.header_comments[name] = prior + tuple(pending)
                pending = []
            continue
        if "=" not in stripped:
            raise LvParseError(f"expected a key=value pair: {stripped!r}", number)
        if current is None:
            raise LvParseError("key found before any section", number)
        key, raw = stripped.split("=", 1)
        current[key.strip()] = _value(raw, tuple(pending))
        pending = []
    config.trailing_comments = tuple(pending)
    return config
