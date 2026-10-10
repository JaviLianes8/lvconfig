"""Serialise a :class:`Config` back to LabVIEW configuration text."""

from __future__ import annotations

from ._config import Config
from ._escape import escape


def dump(config: Config) -> str:
    """Render ``config`` as LabVIEW configuration text.

    Sections and keys are written in their stored order. String and path entries are
    escaped and quoted the way LabVIEW writes them; booleans and numbers stay as bare
    tokens. Sections are separated by a blank line and the text ends with a newline.
    """
    blocks: list[str] = []
    for name, entries in config.sections.items():
        lines = [f"[{name}]"]
        for key, entry in entries.items():
            if entry.quoted:
                lines.append(f'{key}="{escape(entry.value)}"')
            else:
                lines.append(f"{key}={entry.value}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n" if blocks else ""
