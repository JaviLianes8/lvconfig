import pytest

from lvconfig import escape, unescape


def test_escape_encodes_carriage_return_as_hex() -> None:
    assert escape("line\rmore") == "line\\0Dmore"


def test_escape_encodes_newline_and_tab_as_uppercase_hex() -> None:
    assert escape("\n\t") == "\\0A\\09"


def test_escape_doubles_a_backslash() -> None:
    assert escape("C:\\x") == "C:\\\\x"


def test_escape_encodes_the_double_quote() -> None:
    assert escape('say "hi"') == "say \\22hi\\22"


def test_escape_leaves_printable_text_untouched() -> None:
    assert escape("plain text 123") == "plain text 123"


def test_raw_escape_returns_the_input_unchanged() -> None:
    assert escape("line\rmore", raw=True) == "line\rmore"


def test_unescape_decodes_hex_and_doubled_backslash() -> None:
    assert unescape("line\\0Dmore\\\\end") == "line\rmore\\end"


def test_unescape_accepts_lowercase_hex() -> None:
    assert unescape("\\0d") == "\r"


def test_unescape_keeps_an_unknown_escape_verbatim() -> None:
    assert unescape("\\zq") == "\\zq"


@pytest.mark.parametrize("text", ["", 'C:\\log\r\n\ttab"q"', "\x00\x1f\x7f mix"])
def test_escape_round_trips_through_unescape(text: str) -> None:
    assert unescape(escape(text)) == text
