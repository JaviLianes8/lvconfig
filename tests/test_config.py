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


def test_remove_deletes_a_key_and_reports_it() -> None:
    config = Config()
    config.set("A", "x", 1)
    assert config.remove("A", "x") is True
    assert config.remove("A", "x") is False
    assert not config.has("A", "x")


def test_remove_section_drops_its_keys_and_comments() -> None:
    config = Config()
    config.set("A", "x", 1)
    config.header_comments["A"] = ("; note",)
    assert config.remove_section("A") is True
    assert config.section_names() == []
    assert "A" not in config.header_comments


def test_items_returns_decoded_pairs_in_order() -> None:
    config = Config()
    config.set("A", "x", "hi")
    config.set("A", "y", 2)
    assert config.items("A") == [("x", "hi"), ("y", "2")]


def test_to_dict_returns_nested_decoded_values() -> None:
    config = Config()
    config.set("A", "x", "hi")
    config.set("B", "on", True)
    assert config.to_dict() == {"A": {"x": "hi"}, "B": {"on": "TRUE"}}
