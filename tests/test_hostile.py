"""Wrong types, huge input and odd subclasses get typed errors with short messages."""

from __future__ import annotations

import enum
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from lvconfig import (
    Config,
    Entry,
    LvConfigError,
    LvParseError,
    LvPathError,
    dump,
    escape,
    from_labview_path,
    load,
    parse,
    save,
    to_bool,
    to_float,
    to_int,
    to_labview_path,
    unescape,
)
from lvconfig._cli import main

HUGE = "x" * 1_000_000

CALLS: list[Callable[[Any], object]] = [
    parse,
    escape,
    unescape,
    to_bool,
    to_int,
    to_float,
    to_labview_path,
    from_labview_path,
    lambda v: Config().set("A", "k", v),
    lambda v: Config().set(v, "k", 1),
    lambda v: Config().get_str("A", v),
    lambda v: Config().has(v, "k"),
    lambda v: Entry(v, True),
    lambda v: dump(v),
]


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("value", [None, b"bytes", 3j, ["list"], object()])
def test_wrong_types_raise_type_error(call: Callable[[Any], object], value: object) -> None:
    with pytest.raises(TypeError):
        call(value)


@pytest.mark.parametrize(
    "call",
    [
        lambda: parse("[A]\n" + HUGE),
        lambda: to_bool(HUGE),
        lambda: to_int(HUGE),
        lambda: to_float(HUGE),
        lambda: to_labview_path("C:" + HUGE),
        lambda: from_labview_path("/usr/" + HUGE),
        lambda: Config().set("A", HUGE + "=", 1),
        lambda: Config().get_str("A", HUGE),
        lambda: dump(Config(trailing_comments=(HUGE,))),
        lambda: save(Config(), "x.ini", line_ending=HUGE),
    ],
)
def test_error_messages_stay_short_for_huge_input(call: Callable[[], object]) -> None:
    with pytest.raises((LvConfigError, KeyError, ValueError)) as info:
        call()
    assert len(str(info.value)) < 200


def test_a_parse_error_names_its_line() -> None:
    with pytest.raises(LvParseError) as info:
        parse("[A]\r\nx=1\r\n" + "garbage " * 1000)
    assert info.value.line == 3 and str(info.value).startswith("line 3: ")


class Level(enum.IntEnum):
    HIGH = 7


class Loud(float):
    def __repr__(self) -> str:
        return "LOUD"


class Text(str):
    def __str__(self) -> str:
        return "lies"


def test_subclasses_are_written_as_the_value_they_hold() -> None:
    config = Config()
    config.set("A", "level", Level.HIGH)
    config.set("A", "gain", Loud(0.5))
    config.set("A", "name", Text("truth"))
    assert config.items("A") == [("level", "7"), ("gain", "0.5"), ("name", "truth")]
    assert type(config.get_str("A", "name")) is str
    assert escape(Text("a\\b")) == "a\\\\b" and type(escape(Text("ab"))) is str


def test_a_config_filled_with_the_wrong_objects_is_refused_by_dump() -> None:
    for broken in (
        Config(sections={"A": {"k": "not an entry"}}),  # type: ignore[dict-item]
        Config(sections={"A": ["k"]}),  # type: ignore[dict-item]
        Config(sections={1: {}}),  # type: ignore[dict-item]
        Config(trailing_comments=["; c"]),  # type: ignore[arg-type]
        Config(header_comments={"A": ("; c", 3)}, sections={"A": {}}),  # type: ignore[dict-item]
    ):
        with pytest.raises(TypeError):
            dump(broken)


def test_a_refused_config_leaves_the_file_untouched(tmp_path: Path) -> None:
    target = tmp_path / "keep.ini"
    target.write_bytes(b"[A]\r\nx=1")
    config = load(target)
    config.trailing_comments = ("not a comment",)
    with pytest.raises(LvConfigError):
        save(config, target)
    assert target.read_bytes() == b"[A]\r\nx=1"


def test_untouched_lines_are_never_refused_even_when_labview_reads_them_oddly() -> None:
    text = "[A]\nnote = a ; b\n"
    config = parse(text)
    assert dump(config) == text
    with pytest.raises(LvConfigError, match="unquoted"):
        dump(config, normalize=True)
    config.set("A", "note", "a ; b")
    assert dump(config) == '[A]\nnote = "a ; b"\n'


def test_the_cli_reports_a_bad_encoding_without_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "a.ini"
    target.write_bytes(b"[A]\r\nx=1")
    assert main(["--encoding", "no-such-codec", "json", str(target)]) == 1
    assert capsys.readouterr().err.startswith("lvconfig: ")


def test_the_cli_does_not_echo_huge_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["get", "--type", HUGE])
    assert info.value.code == 1
    assert len(capsys.readouterr().err) < 1000


def test_the_cli_reports_undecodable_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "a.ini"
    target.write_bytes(b"[A]\r\nx=\xe9\xff")
    assert main(["json", str(target)]) == 1
    assert "utf-8" in capsys.readouterr().err
    assert main(["--encoding", "cp1252", "json", str(target)]) == 0


def test_the_cli_exits_130_on_an_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from lvconfig import _commands

    def interrupted(*args: object, **kwargs: object) -> object:
        raise KeyboardInterrupt

    monkeypatch.setattr(_commands, "load", interrupted)
    assert main(["json", str(tmp_path / "a.ini")]) == 130
    assert capsys.readouterr().err == ""


def test_path_refusals_are_value_errors_too() -> None:
    with pytest.raises(ValueError):
        to_labview_path("C:relative")
    assert issubclass(LvPathError, ValueError)
