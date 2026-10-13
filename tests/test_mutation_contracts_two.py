"""Contracts for promises the second blind mutation round found unguarded."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import lvconfig
from lvconfig import Config, Entry, LvConfigError, dump, load, parse, save
from lvconfig._cli import main


def _write(tmp_path: Path, name: str, text: str) -> str:
    target = tmp_path / name
    target.write_bytes(text.encode("utf-8"))
    return str(target)


# --- lossless writing ---


def test_a_later_repeated_line_does_not_vouch_for_a_new_bare_value() -> None:
    # LabVIEW reads only the first line; the new value is checked and written for itself.
    config = parse("[S]\nx = 1\nx = \\09a\n")
    config.sections["S"]["x"] = Entry("\ta", quoted=False)
    assert parse(dump(config)).get_str("S", "x") == "\ta"
    config.sections["S"]["x"] = Entry(" a", quoted=False)
    with pytest.raises(LvConfigError):
        dump(config)


def test_unquoting_a_parsed_value_is_checked_like_any_bare_value() -> None:
    config = parse('[S]\nx = " a"\n')
    config.sections["S"]["x"] = Entry(" a", quoted=False)
    with pytest.raises(LvConfigError):
        dump(config)


def test_changing_only_the_quoting_rewrites_the_line() -> None:
    config = parse("[S]\nx = 1\n")
    config.set("S", "x", "1")
    text = dump(config)
    assert text == '[S]\nx = "1"\n'
    assert parse(text).sections["S"]["x"] == Entry("1", quoted=True)


def test_an_edited_bare_value_with_a_semicolon_drops_the_source_trailing_blanks() -> None:
    config = parse("[S]\nx = 1   \n")
    config.sections["S"]["x"] = Entry("a;b", quoted=False)
    text = dump(config)
    assert text == "[S]\nx = a;b\n"
    assert parse(text).get_str("S", "x") == "a;b"


def test_edited_comments_of_a_repeated_section_are_written_once() -> None:
    config = parse("; a\n[S]\nx = 1\n; b\n[S]\ny = 2\n")
    assert config.header_comments == {"S": ("; a", "; b")}
    config.header_comments["S"] = ("; c",)
    text = dump(config)
    assert text == "; c\n[S]\nx = 1\n[S]\ny = 2\n"
    assert parse(text).header_comments == {"S": ("; c",)}


def test_edited_key_comments_keep_the_blank_lines_around_them() -> None:
    config = parse("[S]\n\n; old\nx = 1\n")
    config.sections["S"]["x"] = Entry("1", quoted=False, comments=("; new",))
    assert dump(config) == "[S]\n\n; new\nx = 1\n"


# --- names ---


def test_names_fold_latin_1_capitals_as_labview_does() -> None:
    config = parse("[S]\n\u00c4 = 1\n\u00e4 = 2\n")
    assert config.keys("S") == ["\u00c4"]
    built = Config()
    built.set("S", "\u00c4", 1)
    built.set("S", "\u00e4", 2)
    with pytest.raises(LvConfigError, match="differ only in case"):
        dump(built)


# --- paths ---


def test_get_path_does_not_decode_codes_other_than_tab() -> None:
    config = parse('[P]\nlog = "/C/a\\0Ab"\n')
    assert config.get_str("P", "log") == "/C/a\nb"
    assert config.get_path("P", "log") == "C:\\a\\0Ab"


def test_get_path_returns_a_posix_value_as_stored() -> None:
    config = Config()
    config.set_path("P", "x", "/tmp/a\\b\tc", windows=False)
    assert config.get_path("P", "x", windows=False) == "/tmp/a\\b\tc"


# --- files ---


class _BytesPath(os.PathLike):  # type: ignore[type-arg]
    def __init__(self, path: Path) -> None:
        self.path = path

    def __fspath__(self) -> bytes:
        return os.fsencode(self.path)


def test_a_bytes_path_like_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "a.ini"
    target.write_bytes(b"[A]\nx = 1\n")
    with pytest.raises(TypeError):
        load(_BytesPath(target))
    with pytest.raises(TypeError):
        save(Config(), _BytesPath(target))
    assert target.read_bytes() == b"[A]\nx = 1\n"


def test_load_refuses_an_encoding_that_is_not_a_str(tmp_path: Path) -> None:
    target = tmp_path / "a.ini"
    target.write_bytes(b"[A]\nx = 1\n")
    with pytest.raises(TypeError):
        load(target, encoding=None)  # type: ignore[arg-type]


def test_save_checks_its_arguments_before_the_config(tmp_path: Path) -> None:
    refused = Config(sections={"S": {"k": Entry(" a", quoted=False)}})
    with pytest.raises(TypeError):
        save(refused, tmp_path / "a.ini", encoding=None)  # type: ignore[arg-type]
    assert not (tmp_path / "a.ini").exists()


# --- command line ---


def test_convert_reads_and_writes_in_the_given_encoding(tmp_path: Path) -> None:
    source = tmp_path / "plain.ini"
    source.write_bytes("[S]\nname = caf\u00e9\n".encode("utf-16"))
    target = tmp_path / "lv.ini"
    assert main(["--encoding", "utf-16", "convert", str(source), str(target)]) == 0
    assert target.read_bytes().decode("utf-16") == '[S]\r\nname = "caf\u00e9"'


def test_fmt_writes_its_output_in_the_given_encoding(tmp_path: Path) -> None:
    source = tmp_path / "a.ini"
    source.write_bytes('[S]\nname = "caf\u00e9"\n'.encode("cp1252"))
    target = tmp_path / "b.ini"
    assert main(["--encoding", "cp1252", "fmt", str(source), "-o", str(target)]) == 0
    assert target.read_bytes() == b'[S]\r\nname = "caf\xe9"'


def test_convert_reports_a_malformed_plain_ini_as_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write(tmp_path, "plain.ini", "key = 1\n")
    assert main(["convert", source]) == 1
    assert capsys.readouterr().err.startswith("lvconfig: ")


def test_convert_keeps_text_that_starts_on_a_continuation_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # configparser reads "k =" followed by an indented line as "\nmore".
    source = _write(tmp_path, "plain.ini", "[S]\nk =\n  more\n")
    assert main(["convert", source]) == 0
    assert parse(capsys.readouterr().out).sections["S"]["k"] == Entry("\nmore", quoted=True)


def test_convert_infers_a_number_that_starts_on_a_continuation_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _write(tmp_path, "plain.ini", "[S]\nn =\n  5\n")
    assert main(["convert", source]) == 0
    assert parse(capsys.readouterr().out).sections["S"]["n"] == Entry("5", quoted=False)


def test_errors_are_utf8_whatever_the_pipe_encoding(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.ini", "[A]\nx = 1\n")
    env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = str(Path(lvconfig.__file__).resolve().parent.parent)
    proc = subprocess.run(
        [sys.executable, "-m", "lvconfig._cli", "get", path, "\u4e2d", "x"],
        capture_output=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 1
    assert "\u4e2d" in proc.stderr.decode("utf-8")
