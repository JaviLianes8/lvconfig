"""Serialise a :class:`Config` back to LabVIEW configuration text."""

from __future__ import annotations

from ._config import Config, Entry
from ._escape import escape


def render(entry: Entry) -> str:
    """Return the stored text of one value: quoted and escaped, or a bare token."""
    return f'"{escape(entry.value)}"' if entry.quoted else entry.value


def section_lines(config: Config, name: str) -> list[str]:
    """Return the canonical lines of one section, its header comments first.

    The section ``""`` holds keys that precede every header, so it has no header line.
    """
    lines = list(config.header_comments.get(name, ()))
    if name:
        lines.append(f"[{name}]")
    for key, entry in config.sections[name].items():
        lines.extend(entry.comments)
        lines.append(f"{key}={render(entry)}")
    return lines


def _canonical(config: Config) -> str:
    names = sorted(config.sections, key=bool)  # headerless keys must come first
    blocks = ["\n".join(section_lines(config, name)) for name in names]
    if config.trailing_comments:
        blocks.append("\n".join(config.trailing_comments))
    return "\n\n".join(blocks) + "\n" if blocks else ""


def dump(config: Config, *, normalize: bool = False) -> str:
    """Render ``config`` as LabVIEW configuration text.

    A config returned by :func:`parse` keeps its source layout: every untouched line,
    blank line, comment, line ending and spacing is written back byte for byte, so
    ``dump(parse(text)) == text``. An edited key is rewritten in place with its
    original ``key = `` spacing, a removed key or section disappears with its comments,
    and new keys go after the last key of their section, new sections at the end.

    A config built in code, or any config with ``normalize=True``, is written in the
    canonical form: sections in order separated by a blank line, ``key=value`` with no
    spaces, strings and paths escaped and quoted, booleans and numbers bare, comments
    above their section or key, ``\\n`` line endings and a final newline.
    """
    if config.layout is None or normalize:
        return _canonical(config)
    from ._lossless import write_lossless

    return write_lossless(config, config.layout)
