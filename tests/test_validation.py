"""Anything that would not read back as written is refused, and edge sections survive."""

from pathlib import Path

import pytest

from lvconfig import Config, Entry, LvConfigError, dump, parse
from lvconfig._cli import main


@pytest.mark.parametrize("key", ["k=y", "a\nb", "a\rb", " k", "k ", "; k", "#k"])
def test_set_refuses_a_key_that_would_read_back_differently(key: str) -> None:
    config = Config()
    with pytest.raises(LvConfigError):
        config.set("A", key, "v")
    assert config == Config()


def test_set_refuses_a_section_name_with_a_line_break() -> None:
    with pytest.raises(LvConfigError):
        Config().set("A\nB", "k", 1)


def test_a_bracket_key_is_refused_only_when_it_would_read_as_a_header() -> None:
    config = Config()
    config.set("A", "[x", "quoted]")
    assert parse(dump(config)) == config
    config.sections["A"]["[y"] = Entry("bare]", quoted=False)
    with pytest.raises(LvConfigError, match="header"):
        dump(config)


@pytest.mark.parametrize("value", ['"x"', "'x'", " x", "x\n"])
def test_dump_refuses_a_bare_value_that_would_change(value: str) -> None:
    config = Config()
    config.sections["A"] = {"k": Entry(value, quoted=False)}
    with pytest.raises(LvConfigError):
        dump(config)


@pytest.mark.parametrize("comment", ["x=1", "plain", "; a\n; b"])
def test_dump_refuses_a_comment_that_is_not_a_comment(comment: str) -> None:
    config = parse("[A]\nk=1\n")
    config.trailing_comments = (comment,)
    with pytest.raises(LvConfigError):
        dump(config)


def test_dump_refuses_header_comments_for_a_missing_section() -> None:
    config = parse("[A]\nk=1\n")
    config.header_comments["B"] = ("; orphan",)
    with pytest.raises(LvConfigError, match="missing section"):
        dump(config)


def test_an_empty_unnamed_section_writes_nothing() -> None:
    config = parse("[]\n[a]\nx=1\n")
    assert dump(config, normalize=True) == "[a]\nx=1\n"
    config = parse("k=1\n[a]\nx=1\n")
    config.remove("", "k")
    assert "" not in config.sections
    assert parse(dump(config)) == config
    assert parse(dump(config, normalize=True)) == config


def test_header_comments_of_the_unnamed_section_keep_a_bracket_line() -> None:
    config = parse("; top\n[]\n; c\nk=1\n")
    assert parse(dump(config, normalize=True)) == config
    config = parse("k=1\n[a]\nx=1\n")
    config.header_comments[""] = ("; about the top",)
    assert dump(config) == "; about the top\n[]\nk=1\n[a]\nx=1\n"
    assert parse(dump(config)) == config


def test_set_auto_quotes_a_value_that_looks_quoted(tmp_path: Path) -> None:
    target = tmp_path / "s.ini"
    target.write_bytes(b"[A]\r\nretries = 3\r\n")
    assert main(["set", str(target), "A", "retries", '"x"']) == 0
    assert target.read_bytes() == b'[A]\r\nretries = "\\22x\\22"\r\n'


def test_cli_set_refuses_a_bad_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "s.ini"
    target.write_bytes(b"[A]\r\nk=1\r\n")
    assert main(["set", str(target), "A", "k=y", "v"]) == 1
    assert "contains '='" in capsys.readouterr().err
    assert target.read_bytes() == b"[A]\r\nk=1\r\n"


@pytest.mark.parametrize("token", ["007", "1_000", "1e5", "nan", "infinity", "0x10"])
def test_convert_keeps_unusual_numbers_as_text(
    token: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "plain.ini"
    source.write_text(f"[A]\nv = {token}\n", encoding="utf-8")
    assert main(["convert", str(source)]) == 0
    assert f'v="{token}"' in capsys.readouterr().out


def test_get_and_set_paths_in_posix_form(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "s.ini"
    target.write_bytes(b"[P]\r\nlib=/usr/lib\r\n")
    assert main(["get", str(target), "P", "lib", "--type", "path"]) == 1
    capsys.readouterr()
    assert main(["get", str(target), "P", "lib", "--type", "path", "--posix"]) == 0
    assert capsys.readouterr().out == "/usr/lib\n"
    assert main(["set", str(target), "P", "home", "/home/lv", "--type", "path", "--posix"]) == 0
    assert target.read_bytes() == b'[P]\r\nlib=/usr/lib\r\nhome="/home/lv"\r\n'
