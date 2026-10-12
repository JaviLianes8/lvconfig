"""Contract over the complete promise, checked against hand-written LabVIEW-style files.

The fixtures in ``tests/fixtures/handwritten`` were written for these tests (see the
README there): each one uses a syntax feature LabVIEW's own configuration files use.
No mocks: every test reads the real bytes and runs the real parser, writer and file IO.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lvconfig import LvPathError, dump, from_labview_path, load, parse, save, to_labview_path

FIXTURES = Path(__file__).parent / "fixtures" / "handwritten"
ALL = sorted(path.name for path in FIXTURES.glob("*.ini"))
LABEL = "; Hand-written lvconfig test fixture: "


def _text(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def test_the_fixture_set_is_present_and_keeps_crlf() -> None:
    assert len(ALL) >= 10
    for name in ALL:
        data = (FIXTURES / name).read_bytes()
        assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")
    assert any(not (FIXTURES / name).read_bytes().endswith(b"\r\n") for name in ALL)


@pytest.mark.parametrize("name", ALL)
def test_parse_then_dump_is_byte_identical(name: str) -> None:
    assert dump(parse(_text(name))).encode("utf-8") == (FIXTURES / name).read_bytes()


@pytest.mark.parametrize("name", ALL)
def test_load_then_save_is_byte_identical(name: str, tmp_path: Path) -> None:
    target = tmp_path / name
    save(load(FIXTURES / name), target)
    assert target.read_bytes() == (FIXTURES / name).read_bytes()


@pytest.mark.parametrize("name", ALL)
def test_canonical_form_keeps_every_value(name: str) -> None:
    config = parse(_text(name))
    assert parse(dump(config, normalize=True)) == config


def test_booleans_in_every_spelling_labview_writes() -> None:
    service = parse(_text("service.ini"))
    assert service.get_bool("Service", "PublishStatistics") is False
    assert service.get_bool("Route_2", "RequireKey") is True
    prefs = parse(_text("app_prefs.ini"))
    assert prefs.get_bool("MyApp", "RememberLayout") is True
    assert prefs.get_bool("MyApp", "FirstRun") is False
    rt = parse(_text("target_rt.ini"))
    assert rt.get_bool("Target", "link.tcp.enabled") is False
    assert rt.get_bool("Engine", "WatchdogEnabled") is True
    assert parse(_text("provider.ini")).get_bool("Plugin", "IsPrimary") is True


def test_numbers_strings_and_odd_keys() -> None:
    rt = parse(_text("target_rt.ini"))
    assert rt.get_int("Target", "link.tcp.port") == 4100
    assert rt.get_int("Target", "getDefault->Web.Port") == 8080
    assert rt.get_str("Target", "link.tcp.access") == "+*"
    assert rt.get_str("Target", "link.tcp.serviceName") == "Main Instance/Remote Calls"
    assert parse(_text("provider.ini")).get_float("Plugin", "InterfaceVersion") == 1.0
    device = parse(_text("quoted_device.ini"))
    assert device.get_int("Device", "FamilyCode") == 7
    assert device.get_str("Device", "LinkType") == "Serial / TCP"
    service = parse(_text("service.ini"))
    assert service.get_str("Route_1", "DefaultString") == ""
    assert service.header_comments["Service"] == (
        LABEL + "dashed comment headers, empty values, upper-case booleans.",
        "#------------ Service ------------",
    )


def test_comment_styles_and_headerless_keys() -> None:
    board = parse(_text("commented_keys.ini"))
    assert board.get_str("Board", "DisplayName") == "Bench Board"
    assert board.sections["Board"]["DisplayName"].comments == ("# label shown in menus",)
    tags = parse(_text("semicolon_header.ini"))
    assert tags.header_comments["Tags"] == (LABEL + "server tags for a test target",)
    assert parse(_text("headerless.ini")).get_int("", "MaxEntries") == 250


def test_stored_paths_decode_to_the_right_files() -> None:
    spaced = parse(_text("spaced_path.ini"))
    assert spaced.get_path("Paths", "ToolchainPath") == "C:\\Program Files (x86)\\Toolchain"
    rt = parse(_text("target_rt.ini"))
    assert rt.get_path("Target", "Target.StartupPath") == "c:\\target\\startup"
    assert rt.get_path("Target", "Target.StartupPath", windows=False) == "/c/target/startup"
    remote = parse(_text("remote_windows.ini"))
    assert remote.get_path("Remote", "InstallerPath") == "c:\\Example Installers"
    plugin = parse(_text("provider.ini"))
    assert plugin.get_path("Plugin", "RunnerVI") == "..\\Plugins\\Runner\\Run_Interface.vi"


def test_stored_paths_encode_back_to_the_stored_text() -> None:
    native = "C:\\Program Files (x86)\\Toolchain"
    assert to_labview_path(native) == "/C/Program Files (x86)/Toolchain"
    assert to_labview_path("c:\\target\\startup") == "/c/target/startup"
    stored = "/c/target/www/access.log"
    assert to_labview_path(from_labview_path(stored)) == stored


def test_drive_relative_path_is_refused_not_rewritten() -> None:
    with pytest.raises(LvPathError):
        to_labview_path("C:x")
    with pytest.raises(LvPathError):
        from_labview_path("C:x")
    config = parse(_text("spaced_path.ini"))
    with pytest.raises(LvPathError):
        config.set_path("Paths", "ToolchainPath", "C:Toolchain")
    assert dump(config) == _text("spaced_path.ini")


def test_editing_one_key_leaves_every_other_byte_alone() -> None:
    original = _text("target_rt.ini")
    config = parse(original)
    config.set("Target", "link.tcp.port", 4000)
    config.set_path("Target", "Target.StartupPath", "D:\\apps\\startup")
    expected = original.replace("link.tcp.port=4100", "link.tcp.port=4000").replace(
        "Target.StartupPath=/c/target/startup", 'Target.StartupPath="/D/apps/startup"'
    )
    assert dump(config) == expected


def test_an_edit_keeps_the_original_key_spacing() -> None:
    config = parse(_text("spaced_path.ini"))
    config.set_path("Paths", "ToolchainPath", "D:\\Toolchain")
    assert dump(config).endswith('\r\n[Paths]\r\nToolchainPath = "/D/Toolchain"')
