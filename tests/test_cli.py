import json
from pathlib import Path

import pytest

from lvconfig._cli import main

SAMPLE = (
    '[General]\nname="Rig \\22A\\22"\nenabled=TRUE\nretries=3\n\n[Paths]\nlog="/C/Temp/log.txt"\n'
)


def _write(tmp_path: Path, name: str, text: str) -> str:
    target = tmp_path / name
    target.write_text(text, encoding="utf-8")
    return str(target)


def test_json_dumps_decoded_values(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write(tmp_path, "s.ini", SAMPLE)
    assert main(["json", path]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["General"]["name"] == 'Rig "A"'


def test_json_can_limit_to_a_section(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write(tmp_path, "s.ini", SAMPLE)
    assert main(["json", path, "--section", "Paths"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert list(data) == ["Paths"]


def test_get_reads_a_typed_value(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write(tmp_path, "s.ini", SAMPLE)
    assert main(["get", path, "General", "retries", "--type", "int"]) == 0
    assert capsys.readouterr().out.strip() == "3"


def test_get_decodes_a_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write(tmp_path, "s.ini", SAMPLE)
    assert main(["get", path, "Paths", "log", "--type", "path"]) == 0
    assert capsys.readouterr().out.strip() == "C:\\Temp\\log.txt"


def test_get_missing_key_reports_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "s.ini", SAMPLE)
    assert main(["get", path, "General", "absent"]) == 1
    assert "lvconfig:" in capsys.readouterr().err


def test_convert_escapes_a_plain_ini(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write(tmp_path, "plain.ini", '[General]\nname = Rig "A"\nenabled = true\nretries = 3\n')
    assert main(["convert", path]) == 0
    out = capsys.readouterr().out
    assert 'name="Rig \\22A\\22"' in out
    assert "enabled=TRUE" in out
    assert "retries=3" in out


def test_convert_writes_to_a_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "plain.ini", "[A]\nx = hi\n")
    out = tmp_path / "out.ini"
    assert main(["convert", path, str(out)]) == 0
    assert 'x="hi"' in out.read_text(encoding="utf-8")
