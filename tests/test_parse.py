import pytest

from lvconfig import Config, LvParseError, parse

SAMPLE = """
; a comment line
[General]
name = "Rig \\22A\\22"
enabled = TRUE
retries = 3
threshold = 2.5

[Paths]
log = "/C/Temp/log.txt"
"""


def test_parse_keeps_section_and_key_order() -> None:
    config = parse(SAMPLE)
    assert config.section_names() == ["General", "Paths"]
    assert config.keys("General") == ["name", "enabled", "retries", "threshold"]


def test_parse_decodes_a_quoted_escaped_string() -> None:
    assert parse(SAMPLE).get_str("General", "name") == 'Rig "A"'


def test_parse_reads_typed_values() -> None:
    config = parse(SAMPLE)
    assert config.get_bool("General", "enabled") is True
    assert config.get_int("General", "retries") == 3
    assert config.get_float("General", "threshold") == pytest.approx(2.5)


def test_parse_decodes_a_stored_path_to_windows() -> None:
    assert parse(SAMPLE).get_path("Paths", "log") == "C:\\Temp\\log.txt"


def test_comments_and_blank_lines_are_ignored() -> None:
    assert not parse("; just a comment\n\n").section_names()


def test_repeated_section_merges_its_keys() -> None:
    config = parse("[A]\nx = 1\n[A]\ny = 2\n")
    assert config.keys("A") == ["x", "y"]


def test_a_key_before_any_section_is_rejected() -> None:
    with pytest.raises(LvParseError):
        parse("stray = 1\n")


def test_a_line_without_an_equals_is_rejected() -> None:
    with pytest.raises(LvParseError) as info:
        parse("[A]\nnot a pair\n")
    assert info.value.line == 2


def test_an_empty_text_parses_to_an_empty_config() -> None:
    assert parse("") == Config()
