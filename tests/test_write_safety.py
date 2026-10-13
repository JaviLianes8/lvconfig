"""Writes never half-finish, and dump checks the plain text of every field it writes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from lvconfig import Config, Entry, LvConfigError, dump, load, parse, save


@pytest.mark.skipif(sys.platform != "win32", reason="Windows refuses to replace an open file")
def test_a_save_that_cannot_replace_the_file_leaves_it_whole(tmp_path: Path) -> None:
    target = tmp_path / "big.ini"
    target.write_bytes(b"[A]\r\n" + b"k = 1\r\n" * 5000)
    before = target.read_bytes()
    config = load(target)
    config.set("A", "k", 2)
    with open(target, "rb"), pytest.raises(PermissionError):
        save(config, target)  # the open handle above blocks the replacement
    assert target.read_bytes() == before
    assert [p.name for p in tmp_path.iterdir()] == ["big.ini"]  # no temporary file left


def test_a_save_replaces_the_file_with_the_new_text(tmp_path: Path) -> None:
    target = tmp_path / "a.ini"
    target.write_bytes(b"[A]\r\nk = 1")
    config = load(target)
    config.set("A", "k", 2)
    save(config, target)
    assert target.read_bytes() == b"[A]\r\nk = 2"
    assert [p.name for p in tmp_path.iterdir()] == ["a.ini"]


@pytest.mark.parametrize("value", ["'x;' ", '"a;b"\t', "'v;'"])
def test_a_bare_value_that_reads_as_quoted_after_trimming_is_refused(value: str) -> None:
    config = Config(sections={"S": {"k": Entry(value, quoted=False)}})
    with pytest.raises(LvConfigError, match="unquoted"):
        dump(config)


def test_a_bracket_key_whose_line_would_read_as_a_header_is_refused() -> None:
    config = Config(sections={"S": {"[k": Entry("x;] ", quoted=False)}})
    with pytest.raises(LvConfigError, match="header"):
        dump(config)


class Lying(str):
    def __contains__(self, item: object) -> bool:
        return False

    def startswith(self, *args: object) -> bool:
        return True

    def __format__(self, spec: str) -> str:
        return "evil]\n[Injected"


def test_dump_checks_and_writes_the_plain_text_of_every_field() -> None:
    with pytest.raises(LvConfigError):
        dump(Config(trailing_comments=(Lying("; x\n[Evil]\nk=1"),)))
    config = Config(sections={Lying("S"): {Lying("k"): Entry("1", quoted=False)}})
    assert dump(config) == "[S]\nk = 1"


def test_an_emptied_unnamed_section_keeps_a_bracket_line_in_a_lossless_dump() -> None:
    config = parse("k=1\n[A]\nx=1\n")
    config.sections[""].clear()
    assert parse(dump(config)) == config
