"""Paths with no faithful stored form are refused instead of changing meaning."""

import pytest

from lvconfig import (
    Config,
    LvConfigError,
    LvPathError,
    from_labview_path,
    to_labview_path,
)


@pytest.mark.parametrize("native", ["C:x", "C:dir\\file.txt", "c:", "D:", "C:x/y"])
def test_drive_relative_path_is_refused_on_encode(native: str) -> None:
    with pytest.raises(LvPathError, match="drive-relative"):
        to_labview_path(native)


def test_drive_relative_is_not_rewritten_as_absolute() -> None:
    # The 0.2.0 bug: C:x became /C/x, which reads back as C:\x, a different file.
    with pytest.raises(LvPathError):
        to_labview_path("C:x")


@pytest.mark.parametrize("native", ["\\dir", "\\x\\y"])
def test_rooted_path_without_a_drive_is_refused(native: str) -> None:
    with pytest.raises(LvPathError, match="rooted"):
        to_labview_path(native)


@pytest.mark.parametrize("native", ["\\\\server", "\\\\server\\", "//server", "\\\\\\share"])
def test_unc_path_without_a_share_is_refused(native: str) -> None:
    with pytest.raises(LvPathError, match="UNC"):
        to_labview_path(native)


@pytest.mark.parametrize("native", ["\\\\?\\C:\\x", "\\\\.\\COM1", "//?/C:/x"])
def test_device_path_is_refused(native: str) -> None:
    with pytest.raises(LvPathError, match="device"):
        to_labview_path(native)


@pytest.mark.parametrize("stored", ["C:x", "c:", "\\dir", "//server", "/usr/lib", "/C:/x"])
def test_unfaithful_stored_value_is_refused_on_windows(stored: str) -> None:
    with pytest.raises(LvPathError):
        from_labview_path(stored)


def test_posix_reading_keeps_any_stored_value() -> None:
    assert from_labview_path("/usr/lib", windows=False) == "/usr/lib"
    assert from_labview_path("C:x", windows=False) == "C:x"


def test_forward_slash_windows_input_is_accepted() -> None:
    assert to_labview_path("C:/Temp/log.txt") == "/C/Temp/log.txt"
    assert to_labview_path("//server/share/f") == "//server/share/f"


@pytest.mark.parametrize("native", ["/C/Temp/log.txt", "/a/b", "/dir", "/C:/x", "/C\\x"])
def test_a_forward_slash_rooted_path_is_refused_on_windows(native: str) -> None:
    # On Windows /a/b means \a\b on the current drive, not the drive a:.
    with pytest.raises(LvPathError, match="rooted"):
        to_labview_path(native)


def test_posix_encoding_keeps_the_path() -> None:
    assert to_labview_path("/home/lvuser/natinst", windows=False) == "/home/lvuser/natinst"
    config = Config()
    config.set_path("P", "p", "/usr/local/natinst", windows=False)
    assert config.get_path("P", "p", windows=False) == "/usr/local/natinst"


def test_native_windows_value_is_read_as_is() -> None:
    assert from_labview_path("c:\\NI Installers") == "c:\\NI Installers"


def test_empty_value_is_not_a_path_and_passes_through() -> None:
    assert to_labview_path("") == ""
    assert from_labview_path("") == ""


def test_set_path_refuses_a_drive_relative_value() -> None:
    config = Config()
    with pytest.raises(LvPathError):
        config.set_path("Paths", "log", "C:log.txt")
    assert not config.has("Paths", "log")


def test_path_error_is_a_library_and_value_error() -> None:
    assert issubclass(LvPathError, LvConfigError)
    assert issubclass(LvPathError, ValueError)
