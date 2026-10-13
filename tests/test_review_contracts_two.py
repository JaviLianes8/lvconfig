"""Contracts for the survivors of the independent review's own mutation round."""

from __future__ import annotations

import pytest

from lvconfig import Config, dump, parse


def test_an_exponent_with_a_plus_sign_reads_and_lvconfig_reads_its_own_large_floats() -> None:
    from lvconfig import to_float

    assert to_float("1e+3") == 1000.0
    config = Config()
    config.set("S", "g", 1e22)
    assert dump(config) == "[S]\ng = 1e+22"
    assert parse(dump(config)).get_float("S", "g") == 1e22


@pytest.mark.parametrize("digits", ["12345678901", "-123456789012345678901234567890"])
def test_to_int_keeps_every_digit(digits: str) -> None:
    from lvconfig import to_int

    assert to_int(digits) == int(digits)


def test_the_cli_keeps_a_message_of_exactly_300_characters_whole() -> None:
    from lvconfig._cli import _bounded

    assert _bounded("x" * 300) == "x" * 300
    assert _bounded("x" * 301) == "x" * 300 + "..."


def test_a_key_that_is_not_a_str_is_named_in_the_type_error() -> None:
    config = parse("[S]\nk=1\n")
    with pytest.raises(TypeError, match="key must be a str, not int"):
        config.get_str("S", 5)  # type: ignore[arg-type]


def test_the_multiplication_and_division_signs_are_not_folded() -> None:
    from lvconfig._check import fold

    assert fold("\u00d7") == "\u00d7" and fold("\u00f7") == "\u00f7"
    config = parse("[a\u00d7]\nk=1\n[a\u00f7]\nk=2\n")
    assert config.section_names() == ["a\u00d7", "a\u00f7"]
