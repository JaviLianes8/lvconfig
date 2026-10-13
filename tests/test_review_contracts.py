"""Contracts for the defects the independent QA reviews found, one test per promise."""

from __future__ import annotations

import copy
import pickle
import time
from pathlib import Path

import pytest

from lvconfig import (
    Config,
    Entry,
    LvConfigError,
    LvParseError,
    LvPathError,
    dump,
    load,
    parse,
    save,
)
from lvconfig._cli import main


@pytest.mark.parametrize(
    ("value", "encoding"),
    [("\u4e2d\u6587", "cp1252"), ("\u00e9", "ascii"), ("a\ud800b", "utf-8"), ("x", "no-such")],
)
def test_a_failed_save_leaves_the_file_untouched(value: str, encoding: str, tmp_path: Path) -> None:
    target = tmp_path / "s.ini"
    target.write_bytes(b"[Rig]\r\nname = old")
    config = load(target)
    config.set("Rig", "name", value)
    with pytest.raises((UnicodeEncodeError, LookupError)):
        save(config, target, encoding=encoding)
    assert target.read_bytes() == b"[Rig]\r\nname = old"


def test_a_failed_cli_set_leaves_the_file_untouched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "s.ini"
    target.write_bytes(b"[Rig]\r\nname = old")
    assert main(["--encoding", "cp1252", "set", str(target), "Rig", "name", "\u4e2d"]) == 1
    assert target.read_bytes() == b"[Rig]\r\nname = old"
    assert capsys.readouterr().err.startswith("lvconfig: ")


def test_repeated_sections_with_comments_parse_and_dump_in_linear_time() -> None:
    def cost(n: int) -> float:
        text = "".join(f"; c{i}\n[A]\nk{i}=1\n" for i in range(n))
        start = time.perf_counter()
        config = parse(text)
        assert dump(config) == text
        config.set("A", "k0", 2)
        dump(config)
        return time.perf_counter() - start

    small = min(cost(4000) for _ in range(3))
    large = min(cost(32000) for _ in range(2))
    assert large < small * 8 * 4


def test_an_integer_too_long_to_write_is_an_lvconfig_error() -> None:
    with pytest.raises(LvConfigError, match="too long"):
        Config().set("A", "k", 10**5000)


def test_convert_keeps_a_number_too_long_for_python_as_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plain.ini"
    source.write_text("[A]\nx = " + "7" * 6000 + "\n", encoding="utf-8")
    assert main(["convert", str(source)]) == 0
    assert '"' + "7" * 6000 + '"' in capsys.readouterr().out


def test_a_layout_that_is_not_a_layout_is_a_type_error() -> None:
    config = parse("[A]\nx=1\n")
    config.layout = "junk"  # type: ignore[assignment]
    with pytest.raises(TypeError, match="layout"):
        dump(config)


class BadHash(str):
    def __hash__(self) -> int:
        return 7

    def __eq__(self, other: object) -> bool:
        return False

    __ne__ = str.__ne__


def test_names_are_stored_as_plain_str() -> None:
    config = Config()
    config.set(BadHash("A"), BadHash("k"), 1)
    config.set(BadHash("A"), BadHash("k"), 2)
    assert config.section_names() == ["A"] and config.items("A") == [("k", "2")]
    assert config.remove(BadHash("A"), BadHash("k")) and config.remove_section(BadHash("A"))
    entry = Entry(BadHash("v"), True, (BadHash("; c"),))
    assert type(entry.value) is str and type(entry.comments[0]) is str


def test_an_empty_unnamed_section_survives_a_round_trip() -> None:
    config = Config(sections={"": {}})
    assert dump(config) == "[]"
    assert parse(dump(config)) == config


@pytest.mark.parametrize("comment", ["  ; c", "; c ", "# t\t"])
def test_a_comment_parse_would_trim_is_refused(comment: str) -> None:
    with pytest.raises(LvConfigError):
        dump(Config(trailing_comments=(comment,)))


def test_a_parse_error_survives_pickle_and_copy() -> None:
    error = LvParseError("bad", 3)
    for clone in (pickle.loads(pickle.dumps(error)), copy.copy(error)):
        assert (type(clone), str(clone), clone.line) == (LvParseError, "line 3: bad", 3)


def test_get_with_a_str_default_is_typed_str() -> None:
    config = parse("[A]\nx=1\n")
    sure: str = config.get("A", "missing", "fallback")
    assert sure == "fallback"


@pytest.mark.parametrize("path", ["C:\\..", "C:\\a\\..\\..\\b"])
def test_a_path_above_its_drive_root_is_refused_when_stored(path: str) -> None:
    with pytest.raises(LvPathError, match="climbs"):
        Config().set_path("P", "p", path)


@pytest.mark.parametrize("path", [1, b"x.ini", 3.5])
def test_load_and_save_refuse_paths_of_other_types(path: object) -> None:
    with pytest.raises(TypeError, match="path"):
        load(path)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="path"):
        save(Config(), path)  # type: ignore[arg-type]


def test_cli_lookup_errors_quote_names_briefly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "s.ini"
    target.write_bytes(b"[A]\r\nx=1")
    assert main(["get", str(target), "S" * 1000, "k"]) == 1
    assert len(capsys.readouterr().err) < 120


@pytest.mark.parametrize("path", [r"\\s\sh\..\x", r"\\s\sh\a\..\..\x"])
def test_a_unc_path_above_its_share_is_refused_when_stored(path: str) -> None:
    with pytest.raises(LvPathError, match="climbs"):
        Config().set_path("P", "p", path)


@pytest.mark.parametrize("path", ["C:\a\tb", "rel\nx", "C:\a\x00"])
def test_a_path_with_a_control_character_is_refused_when_stored(path: str) -> None:
    with pytest.raises(LvPathError, match="control character"):
        Config().set_path("P", "p", path)


def test_a_device_path_is_named_as_one_when_read() -> None:
    from lvconfig import from_labview_path

    with pytest.raises(LvPathError, match="device path"):
        from_labview_path(r"\\?\C:\x")


def test_convert_errors_name_the_input_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plain.ini"
    source.write_text("[A]\nx = 1\nx = 2\n", encoding="utf-8")
    assert main(["convert", str(source)]) == 1
    assert "plain.ini" in capsys.readouterr().err
