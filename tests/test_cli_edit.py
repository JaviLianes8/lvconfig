"""The editing commands (set, fmt) and the error contract of the CLI."""

from pathlib import Path

import pytest

from lvconfig._cli import main

FIXTURES = Path(__file__).parent / "fixtures" / "labview2026"


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    target.write_bytes((FIXTURES / name).read_bytes())
    return target


def test_set_edits_one_line_in_place(tmp_path: Path) -> None:
    target = _copy(tmp_path, "def_rtcommon.ini")
    assert main(["set", str(target), "LVRT", "server.tcp.port", "4000"]) == 0
    original = (FIXTURES / "def_rtcommon.ini").read_bytes()
    expected = original.replace(b"server.tcp.port=3363", b"server.tcp.port=4000")
    assert target.read_bytes() == expected


def test_set_auto_keeps_a_quoted_value_quoted(tmp_path: Path) -> None:
    target = _copy(tmp_path, "linx_target_rpi.ini")
    assert main(["set", str(target), "LINX", "IconName", "new.png"]) == 0
    assert b'IconName= "new.png"\r\n' in target.read_bytes()


def test_set_with_types_and_output(tmp_path: Path) -> None:
    source = _copy(tmp_path, "linx_firmware_wizard_config.ini")
    out = tmp_path / "out.ini"
    args = ["set", str(source), "Paths", "ArduinoBasePath", "D:\\Arduino", "--type", "path"]
    assert main([*args, "-o", str(out)]) == 0
    assert out.read_bytes() == b'[Paths]\r\nArduinoBasePath = "/D/Arduino"'
    assert source.read_bytes() == (FIXTURES / "linx_firmware_wizard_config.ini").read_bytes()
    assert main(["set", str(source), "New", "on", "true", "--type", "bool"]) == 0
    assert source.read_bytes().endswith(b"\r\n\r\n[New]\r\non=TRUE")


def test_set_refuses_a_drive_relative_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _copy(tmp_path, "linx_firmware_wizard_config.ini")
    assert main(["set", str(target), "Paths", "p", "C:x", "--type", "path"]) == 1
    assert "drive-relative" in capsys.readouterr().err
    assert target.read_bytes() == (FIXTURES / "linx_firmware_wizard_config.ini").read_bytes()


def test_set_rejects_a_value_of_the_wrong_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _copy(tmp_path, "def_rtcommon.ini")
    assert main(["set", str(target), "LVRT", "server.tcp.port", "x", "--type", "int"]) == 1
    assert "not an integer" in capsys.readouterr().err


def test_fmt_prints_the_canonical_form(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fmt", str(FIXTURES / "linx_firmware_wizard_config.ini")]) == 0
    assert capsys.readouterr().out == '[Paths]\nArduinoBasePath="/C/Program Files (x86)/Arduino"\n'


def test_fmt_writes_crlf_to_a_file(tmp_path: Path) -> None:
    out = tmp_path / "tidy.ini"
    assert main(["fmt", str(FIXTURES / "tags_default.ini"), "-o", str(out)]) == 0
    assert out.read_bytes().startswith(b"; Server tags")
    assert b"\r\nLVSERVER_DOCROOT=" in out.read_bytes()


def test_unknown_section_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["json", str(FIXTURES / "tags_default.ini"), "--section", "Nope"]) == 1
    assert "no section 'Nope'" in capsys.readouterr().err


def test_missing_file_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["get", str(tmp_path / "absent.ini"), "A", "x"]) == 1
    assert capsys.readouterr().err.startswith("lvconfig: ")


def test_usage_errors_exit_one_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["bogus"])
    assert info.value.code == 1
    assert "invalid choice" in capsys.readouterr().err


def test_help_lists_runnable_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--help"])
    assert info.value.code == 0
    out = capsys.readouterr().out
    for command in ("json", "get", "set", "fmt", "convert"):
        assert f"lvconfig {command} settings.ini" in out or f"lvconfig {command} plain" in out
