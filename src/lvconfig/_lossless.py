"""Write a parsed config back over its recorded source layout.

Untouched lines are copied verbatim. Only what the caller changed is rewritten: an
edited value, edited comments, removed keys and sections, and new keys or sections.
"""

from __future__ import annotations

from ._config import Config
from ._dump import render, section_lines
from ._layout import HeaderItem, KeyItem, Layout, RawLine


class _Writer:
    def __init__(self, config: Config, layout: Layout) -> None:
        self.config = config
        self.layout = layout
        self.out: list[RawLine] = []
        self.done_headers: set[str] = set()

    def emit(self, text: str) -> None:
        self.out.append(RawLine(text, self.layout.eol))

    def blanks(self, lead: tuple[RawLine, ...]) -> None:
        self.out.extend(line for line in lead if not line.text.strip())

    def comments(self, lead: tuple[RawLine, ...], current: tuple[str, ...], old: bool) -> None:
        # Unchanged comments are copied verbatim with the blank lines among them.
        if old:
            self.out.extend(lead)
            return
        self.blanks(lead)
        for comment in current:
            self.emit(comment)

    def header(self, item: HeaderItem) -> None:
        name = item.name
        if name not in self.config.sections:
            return
        current = self.config.header_comments.get(name, ())
        unchanged = current == self.layout.headers.get(name, ())
        if unchanged or name not in self.done_headers:
            self.comments(item.lead, current, unchanged)
        else:
            # Edited comments of a repeated section are all written above its first header.
            self.blanks(item.lead)
        self.done_headers.add(name)
        self.out.append(item.line)

    def key(self, item: KeyItem) -> None:
        entries = self.config.sections.get(item.section)
        if entries is None:
            return
        entry = entries.get(item.key)
        if entry is None:
            # A removed key takes its comments along; the spacing around it stays.
            self.blanks(item.lead)
            return
        if item.shadowed:
            self.out.extend(item.lead)
            self.out.append(item.line)
            return
        old = item.entry
        self.comments(item.lead, entry.comments, entry.comments == old.comments)
        if (entry.value, entry.quoted) == (old.value, old.quoted):
            self.out.append(item.line)
        else:
            text = f"{item.prefix}{render(entry)}{item.suffix}"
            self.out.append(RawLine(text, item.line.eol))

    def new_keys(self, name: str, known: set[tuple[str, str]]) -> None:
        for key, entry in self.config.sections.get(name, {}).items():
            if (name, key) not in known:
                for comment in entry.comments:
                    self.emit(comment)
                self.emit(f"{key}={render(entry)}")

    def new_section(self, name: str) -> None:
        if self.out and name:
            self.emit("")
        for text in section_lines(self.config, name):
            self.emit(text)


def write_lossless(config: Config, layout: Layout) -> str:
    """Render ``config`` over ``layout``, rewriting only what changed since parsing."""
    writer = _Writer(config, layout)
    known = {(i.section, i.key) for i in layout.items if isinstance(i, KeyItem)}
    last: dict[str, int] = {}
    for index, item in enumerate(layout.items):
        last[item.name if isinstance(item, HeaderItem) else item.section] = index
    if "" in config.sections and "" not in last:
        writer.new_section("")
    elif config.header_comments.get("") and not any(
        isinstance(item, HeaderItem) and not item.name for item in layout.items
    ):
        # Comments for the unnamed section need a [] line above its keys to stay attached.
        for comment in config.header_comments[""]:
            writer.emit(comment)
        writer.emit("[]")
        writer.done_headers.add("")
    for index, item in enumerate(layout.items):
        if isinstance(item, HeaderItem):
            writer.header(item)
            name = item.name
        else:
            writer.key(item)
            name = item.section
        if last[name] == index and name in config.sections:
            writer.new_keys(name, known)
    for name in config.sections:
        if name and name not in last:
            writer.new_section(name)
    if config.trailing_comments == layout.trailing:
        writer.out.extend(layout.tail)
    else:
        writer.comments(layout.tail, config.trailing_comments, False)
    return layout.bom + _join(writer.out, layout)


def _join(lines: list[RawLine], layout: Layout) -> str:
    if not lines:
        return ""
    parts = [line.text + (line.eol or layout.eol) for line in lines[:-1]]
    parts.append(lines[-1].text + layout.final_eol)
    return "".join(parts)
