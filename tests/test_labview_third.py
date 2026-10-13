"""Contracts against the third LabVIEW 2026 capture run (read_third.json).

Wherever both LabVIEW and lvconfig find a value, it is the same value; where lvconfig
cannot follow LabVIEW it finds nothing or raises. The one case where lvconfig finds a value
LabVIEW cannot see is a key in a later block of a section, a listed difference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lvconfig import LvConfigError, LvParseError, LvPathError, parse

CAPTURE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "labview2026" / "read_third.json").read_text(
        encoding="utf-8"
    )
)
LATER_BLOCK = "[S]\r\n[T]\r\n[s]\r\nk=1\r\n"


@pytest.mark.parametrize("case", CAPTURE["strings"], ids=range(len(CAPTURE["strings"])))
def test_a_found_value_is_labviews_value(case: dict[str, Any]) -> None:
    try:
        got = parse(case["file"]).get(case["section"], case["key"])
    except LvParseError:
        return
    if got is None:
        return
    if case["found"]:
        assert got == case["value"]
    else:
        assert case["file"] == LATER_BLOCK


@pytest.mark.parametrize(("stored", "expected"), list(CAPTURE["bools"].items()))
def test_a_boolean_is_labviews_or_refused(stored: str, expected: bool | None) -> None:
    config = parse(f"[S]\r\nk = {stored}\r\n")
    try:
        got = config.get_bool("S", "k")
    except LvConfigError:
        return
    assert got is expected


@pytest.mark.parametrize("case", CAPTURE["ints"], ids=lambda case: case["stored"])
def test_an_integer_is_labviews_or_refused(case: dict[str, Any]) -> None:
    try:
        got = parse(f"[F]\r\nN = {case['stored']}\r\n").get_int("F", "N")
    except LvConfigError:
        return
    assert case["error"] == 0
    assert min(max(got, -(2**31)), 2**31 - 1) == case["value"]


@pytest.mark.parametrize("case", CAPTURE["paths"], ids=lambda case: case["stored"])
def test_a_path_is_labviews_or_refused(case: dict[str, Any]) -> None:
    try:
        got = parse(f"[F]\r\nP = {case['stored']}\r\n").get_path("F", "P")
    except LvPathError:
        return
    assert got == case["native"]


def test_an_indented_header_names_the_section_labview_writes_back() -> None:
    (case,) = [c for c in CAPTURE["rewrite"] if c["before"].startswith("  [LabVIEW]")]
    names = parse(case["before"]).section_names()
    assert names[0] == " [LabVIEW" and f"[{names[0]}]" in case["after"]
