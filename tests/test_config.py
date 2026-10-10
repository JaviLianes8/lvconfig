import pytest

from lvconfig import Config


def test_get_returns_the_default_when_missing() -> None:
    assert Config().get("A", "x", "fallback") == "fallback"


def test_has_reports_presence() -> None:
    config = Config()
    config.set("A", "x", "v")
    assert config.has("A", "x")
    assert not config.has("A", "y")


def test_get_str_raises_key_error_when_missing() -> None:
    with pytest.raises(KeyError):
        Config().get_str("A", "x")


def test_set_overwrites_without_reordering() -> None:
    config = Config()
    config.set("A", "x", 1)
    config.set("A", "y", 2)
    config.set("A", "x", 9)
    assert config.keys("A") == ["x", "y"]
    assert config.get_int("A", "x") == 9


def test_get_path_can_decode_for_posix() -> None:
    config = Config()
    config.set_path("P", "log", "C:\\Temp\\log.txt")
    assert config.get_path("P", "log", windows=False) == "/C/Temp/log.txt"


def test_keys_of_an_absent_section_is_empty() -> None:
    assert Config().keys("nope") == []
