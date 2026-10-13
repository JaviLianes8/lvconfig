"""Names that differ only in case, repeated blocks and bare comments, as LabVIEW sees them."""

from __future__ import annotations

import pytest

from lvconfig import Config, LvConfigError, dump, parse


def test_a_key_repeated_in_other_case_is_a_repeat_and_the_first_wins() -> None:
    text = "[A]\nX=1\nx=2\n"
    config = parse(text)
    assert config.items("A") == [("X", "1")]
    assert dump(config) == text
    config.set("A", "X", 5)
    assert dump(config) == "[A]\nX=5\nx=2\n"


def test_a_section_repeated_in_other_case_merges_into_the_first_spelling() -> None:
    text = "[S]\nk=1\n[s]\nj=2\n"
    config = parse(text)
    assert config.section_names() == ["S"] and config.items("S") == [("k", "1"), ("j", "2")]
    assert dump(config) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("[S]\nk=1\n[s]\nj=2\n", "[S]\nk=1\nn = 3\n[s]\nj=2\n"),
        ("[A]\na=1\n[B]\nx=1\n[A]\nb=2\n", "[A]\na=1\nn = 3\n[B]\nx=1\n[A]\nb=2\n"),
        ("[A]\n[B]\n[A]\nb=2\n", "[A]\nn = 3\n[B]\n[A]\nb=2\n"),
    ],
)
def test_a_new_key_goes_into_the_first_block_labview_reads(text: str, expected: str) -> None:
    config = parse(text)
    config.set(config.section_names()[0], "n", 3)
    assert dump(config) == expected


@pytest.mark.parametrize(
    "build",
    [
        lambda c: (c.set("S", "x", 1), c.set("S", "X", 2)),
        lambda c: (c.set("A", "x", 1), c.set("a", "y", 2)),
    ],
)
def test_names_that_differ_only_in_case_are_refused_on_dump(build: object) -> None:
    config = Config()
    assert callable(build)
    build(config)
    with pytest.raises(LvConfigError, match="differ only in case"):
        dump(config)


def test_typed_getters_stop_at_a_bare_semicolon_as_labview_does() -> None:
    config = parse('[S]\nb = TRUE ; c\nn = 5;x\nf = 2,5 ; z\nq = "7;"\n')
    assert config.get_str("S", "b") == "TRUE; c"
    assert config.get_bool("S", "b") is True
    assert config.get_int("S", "n") == 5
    assert config.get_float("S", "f") == 2.5
    with pytest.raises(LvConfigError):
        config.get_int("S", "q")  # inside quotes ';' is text


def test_a_stored_path_resolves_its_backslashes_as_labview_does() -> None:
    config = parse('[P]\np = "/C/\\09x"\nq = "/C/a\\\\b"\n')
    assert config.get_path("P", "p") == "C:\\09x"
    assert config.get_path("P", "q") == "C:\\a\\b"
