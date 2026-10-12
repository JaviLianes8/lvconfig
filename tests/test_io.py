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


def test_load_then_save_keeps_the_file_byte_identical(tmp_path: Path) -> None:
    for body in (b"[A]\r\n x = 1\r\n\r\n; c\r\n", b"[A]\nx=1", b"[A]\r\nx=1\ny=2\n"):
        target = tmp_path / "keep.ini"
        target.write_bytes(body)
        save(load(target), target)
        assert target.read_bytes() == body


def test_an_explicit_line_ending_is_forced_on_a_loaded_file(tmp_path: Path) -> None:
    target = tmp_path / "mixed.ini"
    target.write_bytes(b"[A]\nx=1\r\ny=2\n")
    save(load(target), target, line_ending="\r\n")
    assert target.read_bytes() == b"[A]\r\nx=1\r\ny=2\r\n"


def test_an_edit_after_load_keeps_crlf_on_the_new_line(tmp_path: Path) -> None:
    target = tmp_path / "edit.ini"
    target.write_bytes(b"[A]\r\nx=1\r\n")
    config = load(target)
    config.set("A", "y", True)
    save(config, target)
    assert target.read_bytes() == b"[A]\r\nx=1\r\ny=TRUE\r\n"
