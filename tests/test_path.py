import pytest

from lvconfig import from_labview_path, to_labview_path


def test_windows_absolute_path_stores_drive_after_a_slash() -> None:
    assert to_labview_path("C:\\Temp\\log.txt") == "/C/Temp/log.txt"


def test_bare_drive_stores_without_a_trailing_slash() -> None:
    assert to_labview_path("D:\\") == "/D"


def test_unc_path_keeps_a_leading_double_slash() -> None:
    assert to_labview_path("\\\\server\\share\\f") == "//server/share/f"


def test_relative_path_only_swaps_separators() -> None:
    assert to_labview_path("data\\run.ini") == "data/run.ini"


def test_stored_path_decodes_back_to_windows() -> None:
    assert from_labview_path("/C/Temp/log.txt") == "C:\\Temp\\log.txt"


def test_stored_bare_drive_decodes_to_a_root() -> None:
    assert from_labview_path("/D") == "D:\\"


def test_stored_unc_decodes_to_backslashes() -> None:
    assert from_labview_path("//server/share/f") == "\\\\server\\share\\f"


def test_posix_decode_returns_the_stored_form() -> None:
    assert from_labview_path("/C/Temp/log.txt", windows=False) == "/C/Temp/log.txt"


@pytest.mark.parametrize("native", ["C:\\Temp\\log.txt", "E:\\", "data\\run.ini", "a\\b\\c"])
def test_windows_path_round_trips(native: str) -> None:
    assert from_labview_path(to_labview_path(native)) == native
