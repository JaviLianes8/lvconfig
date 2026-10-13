import pytest

from lvconfig import escape, unescape


def test_escape_encodes_carriage_return_as_hex() -> None:
    assert escape("line\rmore") == "line\\0Dmore"


def test_escape_encodes_newline_as_uppercase_hex_and_keeps_tab() -> None:
    assert escape("\n\t\x1b") == "\\0A\t\\1B"


def test_escape_doubles_a_backslash() -> None:
    assert escape("C:\\x") == "C:\\\\x"


def test_escape_keeps_the_double_quote_del_and_high_characters() -> None:
    assert escape('say "hi"\x7f\xe9\u20ac') == 'say "hi"\x7f\xe9\u20ac'


def test_escape_leaves_printable_text_untouched() -> None:
    assert escape("plain text 123") == "plain text 123"


def test_raw_escape_returns_the_input_unchanged() -> None:
    assert escape("line\rmore", raw=True) == "line\rmore"


def test_unescape_decodes_hex_and_doubled_backslash() -> None:
    assert unescape("line\\0Dmore\\\\end") == "line\rmore\\end"


@pytest.mark.parametrize("text", ["\\0d", "\\1f", "\\22", "\\7F", "\\20", "\\E9", "\\zq", "\\"])
def test_unescape_keeps_a_backslash_that_is_not_a_labview_code(text: str) -> None:
    assert unescape(text) == text


def test_unescape_reads_a_doubled_backslash_before_a_code_first() -> None:
    assert unescape("\\\\09") == "\\09"
    assert unescape("\\\\\\09") == "\\\t"


@pytest.mark.parametrize("text", ["", 'C:\\log\r\n\ttab"q"', "\x00\x1f\x7f mix", "\\22\\0a"])
def test_escape_round_trips_through_unescape(text: str) -> None:
    assert unescape(escape(text)) == text


@pytest.mark.parametrize("call", [escape, unescape])
def test_escaping_refuses_text_of_another_type(call: object) -> None:
    assert callable(call)
    with pytest.raises(TypeError, match="must be a str"):
        call(b"bytes")


def test_raw_must_be_a_bool() -> None:
    with pytest.raises(TypeError, match="raw must be a bool"):
        escape("x", raw=1)  # type: ignore[arg-type]
