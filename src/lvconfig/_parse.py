"""Parse LabVIEW configuration text into an ordered :class:`Config`."""

from __future__ import annotations

from dataclasses import replace

from ._config import Config, Entry
from ._errors import LvParseError
from ._escape import unescape
from ._layout import HeaderItem, KeyItem, Layout, RawLine, is_comment, split_lines

_BOM = "\ufeff"


def _value(raw: str, comments: tuple[str, ...]) -> Entry:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        # Quoted strings and paths: the quotes come off and escapes are decoded.
        return Entry(unescape(text[1:-1]), quoted=True, comments=comments)
    return Entry(text, quoted=False, comments=comments)


def _split_key_line(text: str) -> tuple[str, str, str, str]:
    """Return ``(key, value text, prefix, suffix)`` for a ``key=value`` line."""
    left, right = text.split("=", 1)
    body = right.strip()
    start = len(text) - len(right) + (len(right) - len(right.lstrip()))
    prefix = text[:start]
    suffix = text[start + len(body) :]
    return left.strip(), body, prefix, suffix


class _Builder:
    """Collects the config and its layout while walking the source lines."""

    def __init__(self) -> None:
        self.config = Config()
        self.items: list[HeaderItem | KeyItem] = []
        self.current: str | None = None
        self.lead: list[RawLine] = []
        self.comments: list[str] = []
        self.seen: dict[tuple[str, str], int] = {}

    def header(self, name: str, line: RawLine) -> None:
        self.config.sections.setdefault(name, {})
        if self.comments:
            prior = self.config.header_comments.get(name, ())
            self.config.header_comments[name] = prior + tuple(self.comments)
        self.items.append(HeaderItem(name, tuple(self.lead), line))
        self.current = name
        self.lead, self.comments = [], []

    def key(self, line: RawLine) -> None:
        section = "" if self.current is None else self.current
        key, body, prefix, suffix = _split_key_line(line.text)
        entry = _value(body, tuple(self.comments))
        self.config.sections.setdefault(section, {})[key] = entry
        earlier = self.seen.get((section, key))
        if earlier is not None:
            # Last definition wins on read; the earlier line is kept verbatim.
            previous = self.items[earlier]
            assert isinstance(previous, KeyItem)
            self.items[earlier] = replace(previous, shadowed=True)
        self.seen[(section, key)] = len(self.items)
        self.items.append(KeyItem(section, key, tuple(self.lead), line, prefix, suffix, entry))
        self.lead, self.comments = [], []


def parse(text: str) -> Config:
    """Parse configuration text into ordered sections and keys.

    Sections are ``[name]`` headers, keys are ``key = value`` lines, and whole-line
    comments start with ``;`` or ``#``. Comment lines are kept and attached to the
    section or key that follows them. Repeated sections merge in order, and a repeated
    key takes its last value. Keys before the first header go in the section ``""``.
    A non-blank line that is none of the above raises :class:`LvParseError`.

    The returned config records the source layout, so :func:`dump` reproduces
    ``text`` exactly until a value is changed.
    """
    bom = _BOM if text.startswith(_BOM) else ""
    lines = split_lines(text[len(bom) :])
    build = _Builder()
    for number, line in enumerate(lines, start=1):
        stripped = line.text.strip()
        if not stripped or is_comment(stripped):
            build.lead.append(line)
            if stripped:
                build.comments.append(stripped)
        elif stripped.startswith("[") and stripped.endswith("]"):
            build.header(stripped[1:-1], line)
        elif "=" in stripped:
            build.key(line)
        else:
            raise LvParseError(f"expected a key=value pair: {stripped!r}", number)
    config = build.config
    config.trailing_comments = tuple(build.comments)
    eol = next((line.eol for line in lines if line.eol), "\n")
    config.layout = Layout(
        items=tuple(build.items),
        tail=tuple(build.lead),
        headers=dict(config.header_comments),
        trailing=config.trailing_comments,
        bom=bom,
        eol=eol,
        final_eol=lines[-1].eol if lines else eol,
    )
    return config
