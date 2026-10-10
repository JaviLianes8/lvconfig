import math

import pytest

from lvconfig import LvConfigError, to_bool, to_float, to_int


@pytest.mark.parametrize("text", ["TRUE", "true", "True", "1"])
def test_true_tokens_read_as_true(text: str) -> None:
    assert to_bool(text) is True


@pytest.mark.parametrize("text", ["FALSE", "false", "0"])
def test_false_tokens_read_as_false(text: str) -> None:
    assert to_bool(text) is False


def test_a_non_boolean_token_is_rejected() -> None:
    with pytest.raises(LvConfigError):
        to_bool("maybe")


def test_integer_value_parses() -> None:
    assert to_int(" 42 ") == 42


def test_a_non_integer_is_rejected() -> None:
    with pytest.raises(LvConfigError):
        to_int("4.5")


def test_float_value_parses() -> None:
    assert to_float("3.14") == pytest.approx(3.14)


def test_labview_infinity_reads_as_inf() -> None:
    assert math.isinf(to_float("Inf"))


def test_labview_nan_reads_as_nan() -> None:
    assert math.isnan(to_float("NaN"))


def test_a_non_number_is_rejected() -> None:
    with pytest.raises(LvConfigError):
        to_float("abc")
