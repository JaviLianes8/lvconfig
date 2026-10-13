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


def test_an_edit_of_a_key_in_a_later_block_goes_into_the_first_block() -> None:
    text = "[LabVIEW]\r\n[X]\r\n[labview]\r\nLVMode=old\r\n"
    config = parse(text)
    config.set("LabVIEW", "LVMode", "new")
    assert dump(config) == '[LabVIEW]\r\nLVMode = "new"\r\n[X]\r\n[labview]\r\nLVMode=old\r\n'
    assert parse(dump(config)).get("LabVIEW", "LVMode") == "new"


def test_latin_1_capitals_fold_like_ascii_ones() -> None:
    config = parse("[S]\n\u00c9=1\n\u00e9=2\n")
    assert config.items("S") == [("\u00c9", "1")]
    clash = Config()
    clash.set("S", "\u00d8", 1)
    clash.set("S", "\u00f8", 2)
    with pytest.raises(LvConfigError, match="differ only in case"):
        dump(clash)
    sharp = Config()
    sharp.set("S", "\u00df", 1)
    sharp.set("S", "ss", 2)
    assert dump(sharp) == "[S]\n\u00df = 1\nss = 2"


@pytest.mark.parametrize("line", ["[T] x=y", "[T]z=1", '[x = "a]"', "[S] ; note"])
def test_a_line_starting_with_a_bracket_and_holding_one_is_a_header(line: str) -> None:
    config = parse(f"[P]\nk=1\n{line}\nj=2\n")
    assert config.keys("P") == ["k"] and len(config.section_names()) == 2
    assert dump(config) == f"[P]\nk=1\n{line}\nj=2\n"


@pytest.mark.parametrize(
    ("upper", "lower"), [("\u0160", "\u0161"), ("\u0152", "\u0153"), ("\u0178", "\u00ff")]
)
def test_windows_1252_capitals_fold_as_labview_folds_them(upper: str, lower: str) -> None:
    config = parse(f"[S]\n{upper}=1\n{lower}=2\n[{upper}]\na=1\n[{lower}]\na=2\n")
    assert config.items("S") == [(upper, "1")] and config.items(upper) == [("a", "1")]


def test_a_line_of_blanks_is_an_empty_key_to_labview_so_a_later_one_is_not_read() -> None:
    text = "[S]\n \n=v\nk=1\n"
    config = parse(text)
    assert config.get("S", "") is None and config.get("S", "k") == "1"
    assert dump(config) == text
    config.set("S", "k", 2)
    assert dump(config) == "[S]\n \n=v\nk=2\n"
    assert parse("[S]\n\n=v\n").get("S", "") == "v"  # a truly empty line is skipped


def test_a_moved_edit_keeps_its_comments_so_the_config_reads_back_equal() -> None:
    config = parse("[A]\n[A]\n; c\nk=1\n")
    config.set("A", "k", "2")
    assert dump(config) == '[A]\n; c\nk = "2"\n[A]\n; c\nk=1\n'
    assert parse(dump(config)) == config


def test_a_blank_looking_line_before_any_header_adds_no_section() -> None:
    text = " \n=v\n[S]\nk=1\n"
    config = parse(text)
    assert config.section_names() == ["S"]
    assert dump(config) == text


def test_a_moved_key_takes_its_comment_from_a_later_block() -> None:
    config = parse("[A]\n[B]\nb=1\n[A]\nk=1\n; about j\nj=2\n")
    config.set("A", "j", "x")
    assert parse(dump(config)) == config


def test_removing_a_section_keeps_the_blank_looking_line_above_it() -> None:
    config = parse("[A]\n  \n[C]\n[A]\n=x\n")
    config.remove_section("C")
    assert parse(dump(config)) == config


@pytest.mark.parametrize(
    ("text", "remove"),
    [
        ("[Z]\nz=1\n[A]\n \nk=1\n=x\n", ("A", None)),
        ("[A]\na=1\n[B]\n \nb=1\n=x\n", ("B", None)),
        (" \nk=1\n=x\n", ("", "k")),
        (" \nk=1\n=x\n", ("", None)),
    ],
)
def test_a_removal_never_unhides_a_line_behind_a_blank_one(
    text: str, remove: tuple[str, str | None]
) -> None:
    config = parse(text)
    section, key = remove
    if key is None:
        config.remove_section(section)
    else:
        config.remove(section, key)
    assert parse(dump(config)) == config
