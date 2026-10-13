"""Round-trip NI's own configuration file excerpts, when they have been captured locally.

The excerpts are cut from a LabVIEW 2026 install by ``scripts/capture_ni.py`` and are
never committed; ``tests/fixtures/ni/MANIFEST.json`` records their origin. Without them,
these tests skip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lvconfig import dump, parse

FOLDER = Path(__file__).parent / "fixtures" / "ni"
NAMES = sorted(json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))["files"])


def _bytes(name: str) -> bytes:
    path = FOLDER / name
    if not path.is_file():
        pytest.skip(f"{name} absent: run scripts/capture_ni.py")
    return path.read_bytes()


def test_the_manifest_lists_the_captured_files() -> None:
    assert len(NAMES) >= 10


@pytest.mark.parametrize("name", NAMES)
def test_a_captured_file_round_trips_byte_for_byte(name: str) -> None:
    data = _bytes(name)
    assert dump(parse(data.decode("utf-8"))).encode("utf-8") == data


@pytest.mark.parametrize("name", NAMES)
def test_a_captured_file_keeps_every_value_in_canonical_form(name: str) -> None:
    config = parse(_bytes(name).decode("utf-8"))
    assert parse(dump(config, normalize=True)) == config
