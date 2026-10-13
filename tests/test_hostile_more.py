"""Contracts added after the author's mutation round: subclasses, blanks and NaN signs."""

from __future__ import annotations

import pytest

from lvconfig import LvConfigError, escape, from_labview_path, to_float, to_int, to_labview_path


class Text(str):
    def __str__(self) -> str:
        return "lies"


def test_plain_str_comes_back_even_for_a_str_subclass() -> None:
    assert type(escape(Text("ab"), raw=True)) is str
    assert type(to_labview_path(Text("/opt"), windows=False)) is str
    assert type(from_labview_path(Text("/opt"), windows=False)) is str


@pytest.mark.parametrize("text", ["\n5", "5\n", "\x0b5", "\x0c5", "5\r", "\xa05"])
def test_numbers_are_trimmed_of_spaces_and_tabs_only(text: str) -> None:
    for call in (to_int, to_float):
        with pytest.raises(LvConfigError):
            call(text)
    assert to_int(" \t5\t ") == 5


@pytest.mark.parametrize("text", ["-NaN", "+NaN", "-nan", "nan(1)"])
def test_only_an_unsigned_nan_reads_as_nan(text: str) -> None:
    with pytest.raises(LvConfigError):
        to_float(text)
