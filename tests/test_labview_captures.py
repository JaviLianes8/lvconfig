"""Contracts against what LabVIEW 2026 itself wrote and read (tests/fixtures/labview2026).

Each fixture holds inputs chosen for these tests and LabVIEW's own output for them; the
manifest records which shipped VI produced it. Where LabVIEW reads a value lvconfig refuses,
the contract is that lvconfig raises: it never returns a different value.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from lvconfig import Config, LvConfigError, LvPathError, dump, parse, to_bool, to_float

FOLDER = Path(__file__).parent / "fixtures" / "labview2026"


def _load(name: str) -> Any:
    return json.loads((FOLDER / name).read_text(encoding="utf-8"))


WRITES = _load("write_string.json")["cases"]
READS = _load("read_string.json")["cases"]
TYPED = _load("read_typed.json")
REWRITES = _load("rewrite.json")["cases"]
EXAMPLE = _load("write_example.json")["file"]


def test_the_manifest_matches_every_capture() -> None:
    import hashlib

    manifest = _load("manifest.json")
    for name, entry in manifest["files"].items():
        data = (FOLDER / name).read_bytes()
        assert (len(data), hashlib.sha256(data).hexdigest()) == (entry["size"], entry["sha256"])
    assert len(WRITES) == 551 and len(READS) == 812


@pytest.mark.parametrize("case", WRITES, ids=range(len(WRITES)))
def test_a_string_is_written_exactly_as_labview_writes_it(case: dict[str, str]) -> None:
    config = Config()
    config.set("LabVIEW", "LVMode", case["value"])
    assert dump(config) == "[LabVIEW]\n" + case["line"]


@pytest.mark.parametrize("case", READS, ids=range(len(READS)))
def test_a_value_reads_as_labview_reads_it(case: dict[str, str]) -> None:
    config = parse("[S]\r\n" + case["line"] + "\r\n")
    ((_key, value),) = config.items("S")
    assert value == case["value"]


@pytest.mark.parametrize("case", TYPED["paths"], ids=lambda case: case["stored"])
def test_a_path_reads_as_labview_reads_it_or_is_refused(case: dict[str, str]) -> None:
    config = parse(f"[F]\r\nP = {case['stored']}\r\n")
    refused = {'"/usr/lib"', '"/C:/x"', '"C:x"', '"/"', '"//server"', '"/Cx/y"', '"/1/x"'}
    refused.add('"' + "\\" * 4 + "server" + "\\" * 2 + 'share"')
    if case["stored"] in refused:
        with pytest.raises(LvPathError):
            config.get_path("F", "P")
    else:
        assert config.get_path("F", "P") == case["native"]


@pytest.mark.parametrize("case", TYPED["ints"], ids=lambda case: case["stored"])
def test_an_integer_reads_as_labview_reads_it_or_is_refused(case: dict[str, Any]) -> None:
    # The typed getters stop at a bare ';', as LabVIEW's Read Key does.
    token = case["stored"].strip(' "').split(";")[0].strip(" ")
    whole = case["error"] == 0 and token.lstrip("+-").isdigit()
    in_range = whole and -(2**31) <= int(token) < 2**31
    config = parse(f"[F]\r\nN = {case['stored']}\r\n")
    if whole and in_range:
        assert config.get_int("F", "N") == case["value"]
    elif whole:
        assert config.get_int("F", "N") == int(token)  # LabVIEW clamps to I32
    else:
        with pytest.raises(LvConfigError):
            config.get_int("F", "N")


@pytest.mark.parametrize(("stored", "expected"), list(TYPED["bools"].items()))
def test_a_boolean_reads_as_labview_reads_it(stored: str, expected: bool | None) -> None:
    value = parse(f"[F]\r\nB={stored}\r\n").get_str("F", "B")
    if expected is None:
        with pytest.raises(LvConfigError):
            to_bool(value)
    else:
        assert to_bool(value) is expected


@pytest.mark.parametrize(("stored", "expected"), list(TYPED["doubles"].items()))
def test_a_double_reads_as_labview_reads_it_or_is_refused(stored: str, expected: str) -> None:
    value = parse(f"[F]\r\nD = {stored}\r\n").get_str("F", "D")
    labview = float(expected)
    cut_short = {"1_000", "0x10", "1,234,5", "1.234,5", "12abc"}
    if stored in cut_short:
        with pytest.raises(LvConfigError):
            to_float(value)
    elif math.isnan(labview):
        assert math.isnan(to_float(value))
    else:
        assert to_float(value) == labview
        assert math.copysign(1, to_float(value)) == math.copysign(1, labview)


@pytest.mark.parametrize("name", ["blank_lines_lf_final_newline", "empty_file"])
def test_the_canonical_form_is_byte_identical_to_labviews_own_rewrite(name: str) -> None:
    case = REWRITES[name]
    config = parse(case["before"])
    config.set("LabVIEW", "LVMode", "new")
    assert dump(config, normalize=True).replace("\n", "\r\n") == case["after"]


@pytest.mark.parametrize(
    "name",
    ["comments_and_sections", "duplicate_target_key", "repeated_target_section", "escapes_kept"],
)
def test_an_edit_lands_where_labview_puts_it(name: str) -> None:
    case = REWRITES[name]
    config = parse(case["before"])
    config.set("LabVIEW", "LVMode", "new")
    assert parse(dump(config)).to_dict() == parse(case["after"]).to_dict()


def test_the_file_labviews_example_writes_reads_back_typed() -> None:
    config = parse(EXAMPLE)
    assert config.get_bool("Section 1", "Boolean") is True
    assert config.get_float("Section 1", "Double") == 2.0
    assert config.get_path("Section 1", "Path") == "C:\\a\\b\\c.txt"
    assert config.get_str("Section 2", "String1") == "First\nData\nString"
    assert dump(config) == EXAMPLE


def test_the_same_values_built_in_code_give_labviews_bytes() -> None:
    config = Config()
    config.set("Section 1", "Boolean", True)
    config.set("Section 1", "Double", 2.0)
    config.set_path("Section 1", "Path", "C:\\a\\b\\c.txt")
    config.set("Section 2", "String1", "First\nData\nString")
    config.set("Section 2", "String2", "Second Data String")
    ours = dump(config).replace("\n", "\r\n")
    assert ours == EXAMPLE.replace("2,000000", "2.0")
