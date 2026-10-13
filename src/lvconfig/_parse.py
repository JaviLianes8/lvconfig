"""Parse LabVIEW configuration text into an ordered :class:`Config`."""

from __future__ import annotations

from ._check import fold, need_str, short
from ._config import Config
from ._entry import Entry
from ._errors import LvParseError
from ._layout import HeaderItem, KeyItem, Layout, RawLine, is_comment, split_lines
from ._stored import body_of, read, remember

_BOM = "\ufeff"
_BLANK_KEY = "\x00blank"  # marks a key LabVIEW reads from a blank-looking line
_BLANKS = " \t"  # LabVIEW trims spaces and tabs, nothing else


def _split_key_line(text: str) -> tuple[str, str, str, str]:
    """Return ``(key, value text, prefix, suffix)`` for a ``key=value`` line."""
    left, right = text.split("=", 1)
    body = body_of(right)
    start = len(text) - len(right) + (len(right) - len(right.lstrip(_BLANKS)))
    prefix = text[:start]
    suffix = text[start + len(body) :]
    return left.strip(_BLANKS), body, prefix, suffix


class _Builder:
    """Collects the config and its layout while walking the source lines."""

    def __init__(self) -> None:
        self.config = Config()
        self.items: list[HeaderItem | KeyItem] = []
        self.current: str | None = None
        self.lead: list[RawLine] = []
        self.comments: list[str] = []
        self.headers: dict[str, list[str]] = {}  # lists, so repeats stay linear
        # LabVIEW matches names without regard to case: the first spelling stands.
        self.names: dict[str, str] = {}
        self.keys: dict[str, dict[str, str]] = {}

    def header(self, name: str, line: RawLine) -> None:
        name = self.names.setdefault(fold(name), name)
        self.config.sections.setdefault(name, {})
        if self.comments:
            self.headers.setdefault(name, []).extend(self.comments)
        self.items.append(HeaderItem(name, tuple(self.lead), line))
        self.current = name
        self.lead, self.comments = [], []

    def blank_key(self) -> None:
        # LabVIEW reads a line of only spaces or tabs as a key named "" with no value: a
        # later "=..." line is a repeat of it, which lvconfig keeps as text and does not read.
        section = "" if self.current is None else self.current
        self.keys.setdefault(section, {}).setdefault("", _BLANK_KEY)

    def key(self, line: RawLine) -> None:
        section = "" if self.current is None else self.current
        key, body, prefix, suffix = _split_key_line(line.text)
        value, quoted, stored = read(body)
        entry = remember(Entry(value, quoted, tuple(self.comments)), stored)
        seen = self.keys.setdefault(section, {})
        # LabVIEW reads the first line of a repeated key; later ones are kept verbatim and
        # recorded under the first spelling, so they follow that key's fate.
        shadowed = fold(key) in seen
        behind_blank = shadowed and seen[fold(key)] is _BLANK_KEY
        if shadowed and not behind_blank:
            key = seen[fold(key)]
        elif not shadowed:
            seen[fold(key)] = key
            self.config.sections.setdefault(section, {})[key] = entry
        self.items.append(
            KeyItem(
                section, key, tuple(self.lead), line, prefix, suffix, entry, shadowed, behind_blank
            )
        )
        self.lead, self.comments = [], []


def parse(text: str) -> Config:
    r"""Parse configuration text into ordered sections and keys.

    Sections are ``[name]`` headers, keys are ``key = value`` lines, and whole-line
    comments start with ``;`` or ``#``. Comment lines are kept and attached to the
    section or key that follows them. Values are trimmed of spaces and tabs, quotes come
    off, and escapes are decoded in quoted and bare values alike, as LabVIEW reads them.
    A repeated key keeps its first value, the one LabVIEW reads; the later lines stay in
    the text. Repeated sections merge in order. Keys before the first header go in the
    section ``""``. A non-blank line that is none of the above raises
    :class:`LvParseError`.

    The returned config records the source layout, so :func:`dump` reproduces
    ``text`` exactly until a value is changed.

    >>> config = parse('[Rig]\nname = "Bench \\09A"\nretries = 3\nretries = 9\n')
    >>> config.get_str("Rig", "name"), config.get_int("Rig", "retries")
    ('Bench \tA', 3)

    Raises ``TypeError`` when ``text`` is not a ``str``.
    """
    text = need_str("text", text)
    bom = _BOM if text.startswith(_BOM) else ""
    lines = split_lines(text[len(bom) :])
    build = _Builder()
    for number, line in enumerate(lines, start=1):
        stripped = line.text.strip(_BLANKS)
        if not stripped or is_comment(stripped):
            if line.text and not stripped:
                build.blank_key()
            build.lead.append(line)
            if stripped:
                build.comments.append(stripped)
        elif stripped.startswith("[") and "]" in stripped:
            # LabVIEW takes any line starting with '[' and holding ']' as a header, named
            # by what lies between its first character and its last ']'.
            text = line.text.rstrip(_BLANKS)
            build.header(text[1 : text.rindex("]")], line)
        elif "=" in stripped:
            build.key(line)
        else:
            raise LvParseError(f"expected a key=value pair: {short(stripped)}", number)
    config = build.config
    config.header_comments = {name: tuple(lines) for name, lines in build.headers.items()}
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
