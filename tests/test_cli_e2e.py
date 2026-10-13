"""Real end-to-end tests: pip-install the package and drive the installed script.

A throwaway virtual environment gets the project installed into it, and the
installed ``lvconfig`` executable runs as a subprocess against copies of the
hand-written LabVIEW-style fixtures. The assertions read the real process output, exit
status and file bytes; nothing is imported in-process or mocked.
"""

from __future__ import annotations

import json
import subprocess
import sys
import venv
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "handwritten"


@pytest.fixture(scope="module")
def lvconfig_exe(tmp_path_factory: pytest.TempPathFactory) -> Path:
    env_dir = tmp_path_factory.mktemp("venv")
    venv.create(env_dir, with_pip=True)
    scripts = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = scripts / ("python.exe" if sys.platform == "win32" else "python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", str(PROJECT_ROOT)],
        check=True,
        capture_output=True,
        timeout=600,
    )
    exe = scripts / ("lvconfig.exe" if sys.platform == "win32" else "lvconfig")
    assert exe.is_file(), f"console script was not installed at {exe}"
    return exe


def _run(exe: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(exe), *args], capture_output=True, encoding="utf-8", timeout=60)


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    target.write_bytes((FIXTURES / name).read_bytes())
    return target


def test_installed_script_reports_its_version(lvconfig_exe: Path) -> None:
    result = _run(lvconfig_exe, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == "lvconfig 1.0.0"


def test_installed_script_reads_typed_values(lvconfig_exe: Path) -> None:
    rt = str(FIXTURES / "target_rt.ini")
    assert _run(lvconfig_exe, "get", rt, "Target", "link.tcp.port", "--type", "int").stdout == (
        "4100\n"
    )
    result = _run(lvconfig_exe, "get", rt, "Target", "link.tcp.enabled", "--type", "bool")
    assert result.stdout == "False\n"
    linx = str(FIXTURES / "spaced_path.ini")
    result = _run(lvconfig_exe, "get", linx, "Paths", "ToolchainPath", "--type", "path")
    assert result.stdout == "C:\\Program Files (x86)\\Toolchain\n"


def test_installed_script_dumps_json(lvconfig_exe: Path) -> None:
    result = _run(lvconfig_exe, "json", str(FIXTURES / "commented_keys.ini"))
    assert result.returncode == 0
    assert json.loads(result.stdout)["Board"]["DisplayName"] == "Bench Board"


def test_installed_script_edits_one_key_and_keeps_every_other_byte(
    lvconfig_exe: Path, tmp_path: Path
) -> None:
    target = _copy(tmp_path, "service.ini")
    result = _run(lvconfig_exe, "set", str(target), "Service", "RouteCount", "21")
    assert result.returncode == 0, result.stderr
    original = (FIXTURES / "service.ini").read_bytes()
    expected = original.replace(b"RouteCount=12", b"RouteCount=21")
    assert target.read_bytes() == expected


def test_installed_script_refuses_a_drive_relative_path(lvconfig_exe: Path, tmp_path: Path) -> None:
    target = _copy(tmp_path, "spaced_path.ini")
    result = _run(lvconfig_exe, "set", str(target), "Paths", "p", "C:x", "--type", "path")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "drive-relative" in result.stderr
    assert target.read_bytes() == (FIXTURES / "spaced_path.ini").read_bytes()


def test_installed_script_reports_errors_on_stderr(lvconfig_exe: Path) -> None:
    result = _run(lvconfig_exe, "get", str(FIXTURES / "semicolon_header.ini"), "Tags", "absent")
    assert result.returncode == 1
    assert result.stderr.startswith("lvconfig: ")
    usage = _run(lvconfig_exe, "frobnicate")
    assert usage.returncode == 1
    assert "invalid choice" in usage.stderr
