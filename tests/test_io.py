from pathlib import Path

from lvconfig import Config, load, parse, save


def _sample() -> Config:
    config = Config()
    config.set("General", "name", 'Rig "A"\r')
    config.set("General", "enabled", True)
    config.set_path("Paths", "log", "C:\\Temp\\log.txt")
    return config


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    config = _sample()
    target = tmp_path / "settings.ini"
    save(config, target)
    assert load(target) == config


def test_save_writes_crlf_line_endings_by_default(tmp_path: Path) -> None:
    target = tmp_path / "settings.ini"
    save(_sample(), target)
    assert b"\r\n" in target.read_bytes()


def test_save_can_use_plain_newlines(tmp_path: Path) -> None:
    target = tmp_path / "settings.ini"
    save(_sample(), target, line_ending="\n")
    assert b"\r\n" not in target.read_bytes()


def test_load_accepts_a_string_path(tmp_path: Path) -> None:
    target = tmp_path / "settings.ini"
    target.write_text("[A]\nx=1\n", encoding="utf-8")
    assert load(str(target)) == parse("[A]\nx=1\n")
