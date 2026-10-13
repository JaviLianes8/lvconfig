"""Serialise a :class:`Config` back to LabVIEW configuration text."""

from __future__ import annotations

from ._check import need_bool, need_str, type_name
from ._config import Config
from ._entry import Entry
from ._stored import render
from ._validate import check_config


def line(key: str, entry: Entry) -> str:
    """Return one key line in the spacing LabVIEW writes: ``key = value``."""
    return f"{key} = {render(entry)}"


def section_lines(config: Config, name: str) -> list[str]:
    """Return the canonical lines of one section, its header comments first.

    The section ``""`` holds keys that precede every header, so it has no header line
    unless it carries header comments, which need a ``[]`` line to stay attached.
    """
    comments = config.header_comments.get(name, ())
    lines = list(comments)
    entries = config.sections[name]
    if name or comments or not entries:  # an empty unnamed section needs its [] line
        lines.append(f"[{name}]")
    for key, entry in entries.items():
        lines.extend(entry.comments)
        lines.append(line(key, entry))
    return lines


def _canonical(config: Config) -> str:
    names = sorted(config.sections, key=bool)  # headerless keys must come first
    blocks = [lines for lines in (section_lines(config, name) for name in names) if lines]
    if config.trailing_comments:
        blocks.append(list(config.trailing_comments))
    # LabVIEW ends the file right after the last line, with no final newline.
    return protect_bom("\n\n".join("\n".join(lines) for lines in blocks))


def protect_bom(text: str) -> str:
    """Keep a name that starts with U+FEFF intact: parse takes one leading one as a BOM."""
    return "\ufeff" + text if text.startswith("\ufeff") else text


def _plain(config: Config) -> Config:
    """Copy ``config`` with every name and comment as a plain ``str``, checked as such."""
    if not isinstance(config.sections, dict) or not isinstance(config.header_comments, dict):
        raise TypeError("sections and header_comments must be dicts")
    sections: dict[str, dict[str, Entry]] = {}
    for name, entries in config.sections.items():
        if not isinstance(entries, dict):
            raise TypeError(f"section {type_name(name)} must map keys to entries")
        sections[need_str("section name", name)] = {
            need_str("key", key): entry for key, entry in entries.items()
        }
    headers = {
        need_str("section name", name): _comments(comments)
        for name, comments in config.header_comments.items()
    }
    copy = Config(sections, headers, _comments(config.trailing_comments))
    copy.layout = config.layout
    return copy


def _comments(comments: object) -> tuple[str, ...]:
    if not isinstance(comments, tuple):
        raise TypeError(f"comments must be a tuple, not {type_name(comments)}")
    return tuple(need_str("each comment", comment) for comment in comments)


def dump(config: Config, *, normalize: bool = False) -> str:
    r"""Render ``config`` as LabVIEW configuration text.

    A config returned by :func:`parse` keeps its source layout: every untouched line,
    blank line, comment, line ending and spacing is written back byte for byte, so
    ``dump(parse(text)) == text``. An edited key is rewritten in place with its
    original ``key = `` spacing, a removed key or section disappears with its comments,
    new keys go after the section's last line in the source (its last key, or a later
    repeated header), and new sections go at the end.

    A config built in code, or any config with ``normalize=True``, is written in the
    layout LabVIEW's Configuration File VIs write: ``key = value``, a blank line before
    each section header, strings and paths escaped and quoted, booleans and numbers
    bare, comments above their section or key, and no newline after the last line.
    Lines end in ``\n``; :func:`save` writes LabVIEW's ``\r\n``.

    >>> config = Config()
    >>> config.set("Rig", "name", "Bench\n2")
    >>> config.set("Rig", "enabled", True)
    >>> print(dump(config))
    [Rig]
    name = "Bench\0A2"
    enabled = TRUE

    Raises :class:`LvConfigError` when the config holds something that would not read
    back as written: a key with ``=`` or a line break, a bare value with edge blanks,
    surrounding quotes or a blank just before a ``;``, a comment not starting with ``;``
    or ``#`` or ending in blanks, two names that differ only in case, or header comments
    for a missing section. Raises ``TypeError`` for a ``config`` that is not a
    :class:`Config` or a ``normalize`` that is not a ``bool``.
    """
    if not isinstance(config, Config):
        raise TypeError(f"config must be a Config, not {type_name(config)}")
    need_bool("normalize", normalize)
    from ._layout import Layout

    if config.layout is not None and not isinstance(config.layout, Layout):
        raise TypeError(f"layout must be a Layout or None, not {type_name(config.layout)}")
    config = _plain(config)
    if config.layout is None or normalize:
        check_config(config)
        return _canonical(config)
    from ._blocks import kept_keys
    from ._lossless import write_lossless

    check_config(config, kept_keys(config, config.layout))
    return write_lossless(config, config.layout)
