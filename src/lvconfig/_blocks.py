"""What a recorded layout says about blocks: which lines LabVIEW reads and which it cannot.

LabVIEW reads only the first block of a repeated section. A lossless dump therefore puts
new keys into that block, and an edit of a key found only in a later block is written
there too, leaving the old line alone, as LabVIEW's own writer does.
"""

from __future__ import annotations

from ._config import Config
from ._entry import Entry
from ._layout import HeaderItem, KeyItem, Layout


def _first_block_flags(layout: Layout) -> list[bool]:
    """Return, for each layout item, whether it belongs to its section's first block."""
    flags: list[bool] = []
    seen: set[str] = set()
    closed: set[str] = set()
    current = ""
    for item in layout.items:
        if isinstance(item, HeaderItem):
            if current in seen:
                closed.add(current)
            current = item.name
        seen.add(current)
        flags.append(current not in closed)
    return flags


def first_block_ends(layout: Layout) -> dict[str, int]:
    """Map each section to the index of the last item of its first block."""
    last: dict[str, int] = {}
    for index, (item, first) in enumerate(
        zip(layout.items, _first_block_flags(layout), strict=True)
    ):
        if first:
            last[item.name if isinstance(item, HeaderItem) else item.section] = index
    return last


def _live(config: Config, item: KeyItem) -> Entry | None:
    sections = config.sections if isinstance(config.sections, dict) else {}
    entries = sections.get(item.section)
    entry = entries.get(item.key) if isinstance(entries, dict) else None
    return entry if isinstance(entry, Entry) else None


def kept_keys(config: Config, layout: Layout) -> set[tuple[str, str]]:
    """Return the keys whose source line a lossless dump copies unchanged."""
    kept: set[tuple[str, str]] = set()
    for item in layout.items:
        if isinstance(item, KeyItem) and not item.shadowed:
            entry = _live(config, item)
            if entry and (entry.value, entry.quoted) == (item.entry.value, item.entry.quoted):
                kept.add((item.section, item.key))
    return kept


def moved_keys(config: Config, layout: Layout) -> set[tuple[str, str]]:
    """Return the edited keys whose only line sits in a block LabVIEW does not read."""
    moved: set[tuple[str, str]] = set()
    for item, first in zip(layout.items, _first_block_flags(layout), strict=True):
        if isinstance(item, KeyItem) and not item.shadowed and not first:
            entry = _live(config, item)
            if entry and (entry.value, entry.quoted) != (item.entry.value, item.entry.quoted):
                moved.add((item.section, item.key))
    return moved
