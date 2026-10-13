"""The editing commands (set, fmt) and the error contract of the CLI."""

from pathlib import Path

import pytest

from lvconfig._cli import main

FIXTURES = Path(__file__).parent / "fixtures" / "handwritten"


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    target.write_bytes((FIXTURES / name).read_bytes())
    return target


def test_set_edits_one_line_in_place(tmp_path: Path) -> None:
    target = _copy(tmp_path, "target_rt.ini")
    assert main(["set", str(target), "Target", "link.tcp.port", "4000"]) == 0
    original = (FIXTURES / "target_rt.ini").read_bytes()
    expected = original.replace(b"link.tcp.port=4100", b"link.tcp.port=4000")
    assert target.read_bytes() == expected


def test_set_auto_keeps_a_quoted_value_quoted(tmp_path: Path) -> None:
    target = _copy(tmp_path, "commented_keys.ini")
    assert main(["set", str(target), "Board", "IconName", "new.png"]) == 0
    assert b'IconName= "new.png"\r\n' in target.read_bytes()


def test_set_with_types_and_output(tmp_path: Path) -> None:
    source = _copy(tmp_path, "spaced_path.ini")
    out = tmp_path / "out.ini"
    args = ["set", str(source), "Paths", "ToolchainPath", "D:\\Toolchain", "--type", "path"]
    assert main([*args, "-o", str(out)]) == 0
    assert out.read_bytes().endswith(b'\r\n[Paths]\r\nToolchainPath = "/D/Toolchain"')
    assert source.read_bytes() == (FIXTURES / "spaced_path.ini").read_bytes()
    assert main(["set", str(source), "New", "on", "true", "--type", "bool"]) == 0
    assert source.read_bytes().endswith(b"\r\n\r\n[New]\r\non=TRUE")


def test_set_refuses_a_drive_relative_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _copy(tmp_path, "spaced_path.ini")
    assert main(["set", str(target), "Paths", "p", "C:x", "--type", "path"]) == 1
    assert "drive-relative" in capsys.readouterr().err
    assert target.read_bytes() == (FIXTURES / "spaced_path.ini").read_bytes()


def test_set_rejects_a_value_of_the_wrong_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _copy(tmp_path, "target_rt.ini")
    assert main(["set", str(target), "Target", "link.tcp.port", "x", "--type", "int"]) == 1
    assert "not an integer" in capsys.readouterr().err


def test_fmt_prints_the_canonical_form(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fmt", str(FIXTURES / "spaced_path.ini")]) == 0
    out = capsys.readouterr().out
    assert out.endswith('\n[Paths]\nToolchainPath="/C/Program Files (x86)/Toolchain"\n')


def test_fmt_writes_crlf_to_a_file(tmp_path: Path) -> None:
    out = tmp_path / "tidy.ini"
    assert main(["fmt", str(FIXTURES / "semicolon_header.ini"), "-o", str(out)]) == 0
    assert out.read_bytes().startswith(b"; Hand-written")
    assert b"\r\nDOC_ROOT=" in out.read_bytes()


def test_unknown_section_is_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["json", str(FIXTURES / "semicolon_header.ini"), "--section", "Nope"]) == 1
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
