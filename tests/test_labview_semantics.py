"""How lvconfig's reading lines up with LabVIEW's, lookup by lookup (read_semantics.json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lvconfig import LvParseError, parse

CAPTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "labview2026" / "read_semantics.json").read_text(
        encoding="utf-8"
    )
)
TEXT: str = CAPTURE["file"]
LABVIEW = {(row["section"], row["key"]): row for row in CAPTURE["lookups"]}


def test_a_line_labview_reads_as_an_empty_key_is_refused() -> None:
    assert LABVIEW[("S", "noequals line")]["value"] == ""
    with pytest.raises(LvParseError) as info:
        parse(TEXT)
    assert info.value.line == 9


CONFIG = parse(TEXT.replace("noequals line\r\n", ""))


@pytest.mark.parametrize(
    ("section", "key"),
    [("S", "plain"), ("S", "dup"), ("S", "bareesc"), ("S", "spaced key"), (" T ", "sp")],
)
def test_lookups_with_the_exact_names_agree_with_labview(section: str, key: str) -> None:
    assert LABVIEW[(section, key)]["found"] is True
    assert CONFIG.get(section, key) == LABVIEW[(section, key)]["value"]


def test_labview_ignores_case_where_lvconfig_matches_names_exactly() -> None:
    assert LABVIEW[("S", "PLAIN")]["value"] == LABVIEW[("s", "plain")]["value"] == "hello"
    assert CONFIG.get("S", "PLAIN") is None
    assert CONFIG.get("s", "plain") is None


def test_keys_labview_cannot_see_are_still_kept_by_lvconfig() -> None:
    # Before any header, and in a repeated section's later blocks, LabVIEW finds nothing.
    for section, key in [("", "hk"), ("S", "second"), ("S", "lower")]:
        assert LABVIEW[(section, key)]["found"] is False
    assert CONFIG.get("", "hk") == "headless"
    assert CONFIG.get("S", "second") == "block2"
    assert CONFIG.get("S", "lower") == "yes"  # [s] is a later block of [S], as to LabVIEW
    assert CONFIG.section_names() == ["", "S", " T "]


def test_a_semicolon_in_a_bare_value_reads_as_labview_reads_it() -> None:
    assert CONFIG.get("S", "trail") == LABVIEW[("S", "trail")]["value"] == "abc; c"
