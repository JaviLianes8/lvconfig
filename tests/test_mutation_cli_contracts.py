"""CLI contracts that pin promises the blind mutation round showed were unguarded."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import lvconfig
from lvconfig._cli import main


def _write(tmp_path: Path, name: str, text: str) -> str:
    target = tmp_path / name
    target.write_bytes(text.encode("utf-8"))
    return str(target)


def test_a_closed_pipe_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class ClosedPipe:
        def write(self, text: str) -> int:
            raise BrokenPipeError

        def flush(self) -> None:
            raise BrokenPipeError

    path = _write(tmp_path, "a.ini", "[A]\nx = 1\n")
    monkeypatch.setattr(sys, "stdout", ClosedPipe())
    assert main(["json", path]) == 1


def test_output_is_utf8_whatever_the_pipe_encoding(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.ini", '[A]\nname = "\u4e2d\u20ac"\n')
    env = dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1")
    env["PYTHONPATH"] = str(Path(lvconfig.__file__).resolve().parent.parent)
    proc = subprocess.run(
        [sys.executable, "-m", "lvconfig._cli", "get", path, "A", "name"],
        capture_output=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.decode("utf-8").strip() == "\u4e2d\u20ac"


def test_json_keeps_non_ascii_text_readable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "a.ini", '[A]\nname = "caf\u00e9"\n')
    assert main(["json", path]) == 0
    out = capsys.readouterr().out
    assert "caf\u00e9" in out
    assert "\\u00e9" not in out
    assert json.loads(out) == {"A": {"name": "caf\u00e9"}}


def test_convert_infers_only_true_false_ints_and_plain_decimals(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = "[S]\nMixedCase = yes\nflag = no\nrate = 50%\ngain = 2.5\non = true\n"
    path = _write(tmp_path, "plain.ini", text)
    assert main(["convert", path]) == 0
    assert capsys.readouterr().out == (
        '[S]\nMixedCase = "yes"\nflag = "no"\nrate = "50%"\ngain = 2.5\non = TRUE'
    )


def test_set_auto_keeps_the_comment_of_a_bare_key(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.ini", "[A]\n; how many\nx = 1\n")
    assert main(["set", path, "A", "x", "2"]) == 0
    assert Path(path).read_bytes() == b"[A]\n; how many\nx = 2\n"


def test_set_type_str_quotes_even_a_bare_key(tmp_path: Path) -> None:
    path = _write(tmp_path, "a.ini", "[A]\nx = 1\n")
    assert main(["set", path, "A", "x", "5", "--type", "str"]) == 0
    assert Path(path).read_bytes() == b'[A]\nx = "5"\n'


def test_get_names_the_missing_section(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write(tmp_path, "a.ini", "[A]\nx = 1\n")
    assert main(["get", path, "B", "x"]) == 1
    assert capsys.readouterr().err == "lvconfig: no section 'B'\n"
