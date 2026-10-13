"""Contracts pinned by the third blind mutation round."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lvconfig import Config, LvPathError, dump, from_labview_path, parse, save

BOM = chr(0xFEFF)


def test_a_key_repeated_in_a_later_block_of_its_section_is_not_written_twice() -> None:
    text = "[A]\nk=1\n[B]\nx=1\n[A]\nk=2\n"
    config = parse(text)
    assert dump(config) == text
    config.set("B", "x", 5)
    assert dump(config) == "[A]\nk=1\n[B]\nx=5\n[A]\nk=2\n"


def test_an_edited_key_of_a_later_block_takes_its_comments_along() -> None:
    config = parse("[A]\nx=1\n[B]\ny=1\n[A]\n; note\nk=1\n")
    config.set("A", "k", 2)
    out = dump(config)
    assert out == "[A]\nx=1\n; note\nk = 2\n[B]\ny=1\n[A]\n; note\nk=1\n"
    assert parse(out) == config


def test_a_new_headerless_key_starting_with_a_bom_character_survives_a_lossless_dump() -> None:
    config = parse("[A]\nx=1\n")
    config.set("", BOM + "k", 1)
    out = dump(config)
    assert out.startswith(BOM + BOM + "k = 1")
    assert parse(out).keys("") == [BOM + "k"]


@pytest.mark.parametrize("path", ["/C:/x", "/C:", r"/c\x"])
def test_a_malformed_drive_is_refused_as_malformed_not_as_a_posix_path(path: str) -> None:
    with pytest.raises(LvPathError, match="malformed drive component"):
        from_labview_path(path)


def test_a_drive_path_holding_a_line_break_still_resolves_as_a_drive_path() -> None:
    assert from_labview_path("/C/a\nb/c") == "C:\\a\nb\\c"


@pytest.mark.parametrize("upper", [chr(0xC0), chr(0xC9), chr(0xDE)])
def test_every_latin1_capital_folds_when_names_are_compared(upper: str) -> None:
    config = parse(f"[{upper}]\nk=1\n[{upper.lower()}]\nj=2\n")
    assert config.section_names() == [upper]
    assert config.keys(upper) == ["k", "j"]


@pytest.mark.parametrize("upper", [chr(0x100), chr(0x391), chr(0x410)])
def test_capitals_beyond_latin1_do_not_fold(upper: str) -> None:
    config = parse(f"[{upper}]\nk=1\n[{upper.lower()}]\nk=2\n")
    assert config.section_names() == [upper, upper.lower()]


def test_a_save_replaces_the_target_from_a_temporary_file_in_its_own_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    replaced: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(source: str, target: str) -> None:
        replaced.append((os.fspath(source), os.fspath(target)))
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", spy)
    target = tmp_path / "rig.ini"
    config = Config()
    config.set("Rig", "retries", 3)
    save(config, target)
    assert target.read_bytes() == b"[Rig]\r\nretries = 3"
    assert len(replaced) == 1
    source, written = replaced[0]
    assert Path(written) == target
    assert Path(source).parent == tmp_path
    assert sorted(p.name for p in tmp_path.iterdir()) == ["rig.ini"]
