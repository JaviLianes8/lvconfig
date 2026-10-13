"""Contracts against the second LabVIEW 2026 capture run (read_more.json).

Every lookup either agrees with LabVIEW or is one of the differences GUIDE.md lists, and
in those lvconfig finds nothing or raises: it never returns a value LabVIEW would not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lvconfig import LvConfigError, LvParseError, LvPathError, dump, parse

CAPTURE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "labview2026" / "read_more.json").read_text(
        encoding="utf-8"
    )
)
STRINGS = CAPTURE["strings"]
# Index: lvconfig finds nothing where LabVIEW finds a value (documented differences).
ABSENT_HERE = {28: "case", 30: "# line is a comment", 31: "; line", 32: "; line"}
# Index: lvconfig finds a value where LabVIEW finds nothing (documented differences).
FOUND_HERE = {38: "indented header", 42: "[] section", 44: "later block"}
REFUSED = {39: "header with a comment", 40: "header with a comment", 48: "BOM in latin-1"}


@pytest.mark.parametrize("index", range(len(STRINGS)))
def test_a_string_lookup_agrees_with_labview_or_is_a_listed_difference(index: int) -> None:
    case = STRINGS[index]
    if index in REFUSED:
        with pytest.raises(LvParseError):
            parse(case["file"])
        return
    got = parse(case["file"]).get(case["section"], case["key"])
    if index in ABSENT_HERE:
        assert case["found"] and got is None
    elif index in FOUND_HERE:
        assert not case["found"] and got is not None
    else:
        assert (got if got is not None else "<absent>") == case["value"]


@pytest.mark.parametrize(("stored", "expected"), list(CAPTURE["bools"].items()))
def test_a_boolean_reads_as_labview_reads_it_or_is_refused(
    stored: str, expected: bool | None
) -> None:
    config = parse(f"[S]\r\nk = {stored}\r\n")
    if expected is None:
        with pytest.raises(LvConfigError):
            config.get_bool("S", "k")
    else:
        assert config.get_bool("S", "k") is expected


@pytest.mark.parametrize("case", CAPTURE["paths"], ids=lambda case: case["stored"])
def test_a_path_reads_as_labview_reads_it_or_is_refused(case: dict[str, Any]) -> None:
    config = parse(f"[F]\r\nP = {case['stored']}\r\n")
    try:
        got = config.get_path("F", "P")
    except LvPathError:
        # Refused: a bare drive, a climb above the root or share, or an incomplete UNC.
        assert case["native"] in {"C:\\", "", "x:\\", "x", "\\\\dir\\", "\\\\\\x"}
        return
    assert got == case["native"]


@pytest.mark.parametrize("case", CAPTURE["ints"], ids=lambda case: case["stored"])
def test_an_integer_reads_as_labview_reads_it_or_is_refused(case: dict[str, Any]) -> None:
    config = parse(f"[F]\r\nN = {case['stored']}\r\n")
    try:
        got = config.get_int("F", "N")
    except LvConfigError:
        return
    assert case["error"] == 0
    clamped = min(max(got, -(2**31)), 2**31 - 1)
    assert clamped == case["value"]


@pytest.mark.parametrize("case", CAPTURE["rewrite"], ids=range(len(CAPTURE["rewrite"])))
def test_files_labview_rewrote_read_back_with_what_labview_kept(case: dict[str, Any]) -> None:
    try:
        before = parse(case["before"])
    except LvParseError:
        return  # a header with a comment, refused (listed in the GUIDE)
    assert parse(dump(before)) == before
    after = parse(case["after"])
    written = [
        value
        for name in after.section_names()
        if name.lower() == "labview"
        for key, value in after.items(name)
        if key.lower() == "lvmode"
    ]
    assert written[0] == case.get("value", "new")
    for name in before.section_names():
        if name.lower() != "labview":
            for key, value in before.items(name):
                assert after.get(name, key) == value
