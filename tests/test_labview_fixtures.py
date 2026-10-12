"""Contract over the complete promise, checked against files LabVIEW 2026 wrote.

The fixtures are verbatim excerpts of files installed with LabVIEW 2026; their
source paths are listed in ``tests/fixtures/labview2026/SOURCES.txt``. No mocks:
every test reads the real bytes and runs the real parser, writer and file IO.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lvconfig import LvPathError, dump, from_labview_path, load, parse, save, to_labview_path

FIXTURES = Path(__file__).parent / "fixtures" / "labview2026"
ALL = sorted(path.name for path in FIXTURES.glob("*.ini"))


def _text(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def test_the_fixture_set_is_present_and_keeps_crlf() -> None:
    assert len(ALL) >= 10
    for name in ALL:
        data = (FIXTURES / name).read_bytes()
        assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")


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
    assert parse(_text("webservice_sysadmin.ini")).get_bool("Service", "PublishStatistics") is False
    assert parse(_text("labview_ini_excerpt.ini")).get_bool("LabVIEW", "saveFloaterLocations")
    rt = parse(_text("def_rtcommon.ini"))
    assert rt.get_bool("LVRT", "server.tcp.enabled") is False
    assert rt.get_bool("LabVIEW", "ResponsivenessCheckEnabled") is True
    assert parse(_text("exe_provider.ini")).get_bool("Provider", "IsPrimary") is True


def test_numbers_strings_and_odd_keys() -> None:
    rt = parse(_text("def_rtcommon.ini"))
    assert rt.get_int("LVRT", "server.tcp.port") == 3363
    assert rt.get_int("LVRT", "getDefault->WebServer.Port") == 80
    assert rt.get_str("LVRT", "server.tcp.access") == "+*"
    assert rt.get_str("LVRT", "server.tcp.serviceName") == "Main Application Instance/VI Server"
    assert parse(_text("exe_provider.ini")).get_float("Provider", "InterfaceVersion") == 1.0
    uno = parse(_text("arduino_uno_dev.ini"))
    assert uno.get_int("General", "FamilyID") == 2
    assert uno.get_str("General", "FirmwareProgramInterface") == "Serial / USB"
    ws = parse(_text("webservice_sysadmin.ini"))
    assert ws.get_str("RoutingTemplate_1", "DefaultString") == ""
    assert ws.header_comments["Service"] == ("#-------------- Service --------------------------",)


def test_comment_styles_and_headerless_keys() -> None:
    rpi = parse(_text("linx_target_rpi.ini"))
    assert rpi.get_str("LINX", "NiceName") == "Raspberry Pi"
    assert rpi.sections["LINX"]["NiceName"].comments == ("# name shown in wizards and menus",)
    tags = parse(_text("tags_default.ini"))
    assert tags.header_comments["Tags"] == ("; Server tags for standard VxWorks/Pharlap targets",)
    assert parse(_text("mx_lv_provider.ini")).get_int("", "MaxTraceEntries") == 300


def test_stored_paths_decode_to_the_right_files() -> None:
    linx = parse(_text("linx_firmware_wizard_config.ini"))
    assert linx.get_path("Paths", "ArduinoBasePath") == "C:\\Program Files (x86)\\Arduino"
    rt = parse(_text("def_rtcommon.ini"))
    assert rt.get_path("LVRT", "RTTarget.VIPath") == "c:\\ni-rt\\startup"
    assert rt.get_path("LVRT", "RTTarget.VIPath", windows=False) == "/c/ni-rt/startup"
    remote = parse(_text("def_remote_windows_common.ini"))
    native = "c:\\NI Installers"
    assert remote.get_path("LVREMOTEWINDOWS", "Deployment_DownloadInstallerPath") == native
    exe = parse(_text("exe_provider.ini"))
    assert exe.get_path("Provider", "BuildInterfaceVI") == "..\\Builds\\EXE\\EBUIP_Build_Interface.vi"


def test_stored_paths_encode_back_to_the_stored_text() -> None:
    assert to_labview_path("C:\\Program Files (x86)\\Arduino") == "/C/Program Files (x86)/Arduino"
    assert to_labview_path("c:\\ni-rt\\startup") == "/c/ni-rt/startup"
    stored = "/c/ni-rt/system/www/www.log"
    assert to_labview_path(from_labview_path(stored)) == stored


def test_drive_relative_path_is_refused_not_rewritten() -> None:
    with pytest.raises(LvPathError):
        to_labview_path("C:x")
    with pytest.raises(LvPathError):
        from_labview_path("C:x")
    config = parse(_text("linx_firmware_wizard_config.ini"))
    with pytest.raises(LvPathError):
        config.set_path("Paths", "ArduinoBasePath", "C:Arduino")
    assert dump(config) == _text("linx_firmware_wizard_config.ini")


def test_editing_one_key_leaves_every_other_byte_alone() -> None:
    original = _text("def_rtcommon.ini")
    config = parse(original)
    config.set("LVRT", "server.tcp.port", 4000)
    config.set_path("LVRT", "RTTarget.VIPath", "D:\\apps\\startup")
    expected = original.replace("server.tcp.port=3363", "server.tcp.port=4000").replace(
        "RTTarget.VIPath=/c/ni-rt/startup", 'RTTarget.VIPath="/D/apps/startup"'
    )
    assert dump(config) == expected


def test_an_edit_keeps_the_original_key_spacing() -> None:
    config = parse(_text("linx_firmware_wizard_config.ini"))
    config.set_path("Paths", "ArduinoBasePath", "D:\\Arduino")
    assert dump(config) == '[Paths]\r\nArduinoBasePath = "/D/Arduino"'
