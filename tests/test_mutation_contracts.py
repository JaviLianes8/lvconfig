"""Contracts that pin promises the blind mutation round showed were unguarded."""

from __future__ import annotations

from pathlib import Path

import pytest

from lvconfig import (
    Config,
    Entry,
    LvConfigError,
    dump,
    parse,
    save,
    to_bool,
    to_int,
)


def test_to_bool_trims_only_spaces_and_tabs() -> None:
    assert to_bool(" \tTRUE\t ") is True
    for text in ("TRUE\n", "\x0bTRUE", "TRUE\r", chr(0xA0) + "TRUE"):
        with pytest.raises(LvConfigError):
            to_bool(text)


def test_error_message_quotes_exactly_forty_characters_in_full() -> None:
    with pytest.raises(LvConfigError) as forty:
        to_int("x" * 40)
    assert repr("x" * 40) in str(forty.value)
    assert "characters" not in str(forty.value)
    with pytest.raises(LvConfigError) as longer:
        to_int("x" * 41)
    assert "(41 characters)" in str(longer.value)
    assert repr("x" * 41) not in str(longer.value)


def test_type_error_message_bounds_a_huge_type_name() -> None:
    huge = type("T" * 5000, (), {})
    with pytest.raises(TypeError) as info:
        Config().set("A", "x", huge())
    assert len(str(info.value)) < 200


def test_str_subclass_is_read_by_its_plain_text() -> None:
    class Sneaky(str):
        def strip(self, chars: str | None = None) -> str:
            return "TRUE"

        def lower(self) -> str:
            return "true"

    assert to_bool(Sneaky("no")) is False


def test_int_subclass_is_written_by_its_number_not_its_str() -> None:
    class Odd(int):
        def __str__(self) -> str:
            return "not a number"

    config = Config()
    config.set("A", "n", Odd(5))
    assert config.sections["A"]["n"] == Entry("5", quoted=False)


def test_entry_refuses_a_list_of_comments() -> None:
    with pytest.raises(TypeError):
        Entry("x", quoted=False, comments=["; c"])  # type: ignore[arg-type]


def test_lone_quote_value_is_a_bare_quote_character() -> None:
    config = parse("[A]\nx = \"\ny = '\n")
    assert config.sections["A"]["x"] == Entry('"', quoted=False)
    assert config.sections["A"]["y"] == Entry("'", quoted=False)


def test_repeated_section_merges_its_header_comments_in_order() -> None:
    config = parse("; first\n[S]\nx = 1\n; second\n[S]\ny = 2\n")
    assert config.header_comments["S"] == ("; first", "; second")


def test_input_without_any_line_break_gets_lf_for_new_lines() -> None:
    config = parse("[A]")
    config.set("A", "k", 1)
    assert dump(config) == "[A]\nk = 1"


def test_new_trailing_comment_after_final_newline_adds_no_blank_line() -> None:
    config = parse("[A]\nx = 1\n")
    config.trailing_comments = ("; end",)
    assert dump(config) == "[A]\nx = 1\n; end\n"


def test_section_name_with_carriage_return_is_refused() -> None:
    with pytest.raises(LvConfigError):
        Config().set("a\rb", "k", 1)
    config = Config(sections={"a\rb": {"k": Entry("1", quoted=False)}})
    with pytest.raises(LvConfigError):
        dump(config)


def test_key_with_edge_tab_is_refused() -> None:
    for key in ("\tk", "k\t"):
        with pytest.raises(LvConfigError):
            Config().set("A", key, 1)


def test_comment_must_start_with_semicolon_or_hash() -> None:
    config = Config()
    config.set("A", "x", 1)
    for bad in ("// note", "/ note", "note"):
        config.header_comments["A"] = (bad,)
        with pytest.raises(LvConfigError):
            dump(config)


def test_removing_last_headerless_key_keeps_section_with_comments() -> None:
    config = Config()
    config.set("", "x", 1)
    config.set("A", "y", 2)
    config.header_comments[""] = ("; top",)
    assert config.remove("", "x") is True
    assert "" in config.sections
    assert dump(config) == "; top\n[]\n\n[A]\ny = 2"


def test_edited_key_keeps_its_own_line_ending() -> None:
    config = parse("[A]\nx = 1\r\ny = 2\n")
    config.set("A", "x", 5)
    assert dump(config) == "[A]\nx = 5\r\ny = 2\n"


def test_new_section_in_empty_parsed_text_has_no_leading_blank_line() -> None:
    config = parse("")
    config.set("A", "x", 1)
    assert dump(config) == "[A]\nx = 1\n"


def test_shadowed_line_does_not_excuse_an_unsafe_bare_value() -> None:
    config = parse("[A]\nx = 1\nx = a ;b\n")
    config.sections["A"]["x"] = Entry("a ;b", quoted=False)
    with pytest.raises(LvConfigError):
        dump(config)


def test_new_key_in_parsed_config_keeps_its_comments() -> None:
    config = parse("[A]\nx = 1\n")
    config.sections["A"]["y"] = Entry("2", quoted=False, comments=("; why",))
    assert dump(config) == "[A]\nx = 1\n; why\ny = 2\n"


def test_save_accepts_a_bare_cr_line_ending(tmp_path: Path) -> None:
    config = Config()
    config.set("A", "x", 1)
    config.set("A", "y", 2)
    path = tmp_path / "cr.ini"
    save(config, path, line_ending="\r")
    assert path.read_bytes() == b"[A]\rx = 1\ry = 2"
