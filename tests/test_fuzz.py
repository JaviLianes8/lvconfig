"""Seeded property tests: arbitrary text and values never crash, hang or lose a byte."""

from __future__ import annotations

import contextlib
import random
import time

import pytest

from lvconfig import (
    Config,
    LvConfigError,
    LvParseError,
    LvPathError,
    dump,
    escape,
    from_labview_path,
    parse,
    to_bool,
    to_float,
    to_int,
    to_labview_path,
    unescape,
)

SEED = 20261013
PIECES = [
    "[",
    "]",
    "=",
    ";",
    "#",
    "\\",
    "\\\\",
    "\\0A",
    "\\1F",
    "\\22",
    '"',
    "'",
    " ",
    "\t",
    "\r",
    "\n",
    "\r\n",
    "a",
    "Z",
    "0",
    "9",
    ",",
    ".",
    "/",
    ":",
    "\x00",
    "\x1f",
    "\x7f",
    "\xa0",
    "\u00e9",
    "\u20ac",
    "\ufeff",
    "\U0001f600",
    "TRUE",
    "C:",
    "//",
    "..",
    "x = 1",
]


def _text(rnd: random.Random, size: int) -> str:
    return "".join(rnd.choice(PIECES) for _ in range(rnd.randint(0, size)))


def test_any_text_parses_or_raises_a_parse_error_and_round_trips() -> None:
    rnd = random.Random(SEED)
    parsed = 0
    for _ in range(6000):
        text = _text(rnd, 30)
        try:
            config = parse(text)
        except LvParseError:
            continue
        parsed += 1
        assert dump(config) == text
        try:
            canonical = dump(config, normalize=True)
        except LvConfigError:
            # Only a bare value LabVIEW would cut at ';' cannot be rewritten as it is.
            bare = [e.value for es in config.sections.values() for e in es.values() if not e.quoted]
            assert any(";" in value for value in bare)
            continue
        assert parse(canonical) == config
    assert parsed > 1000


def _value(rnd: random.Random) -> str | bool | int | float:
    kind = rnd.randrange(4)
    if kind == 0:
        return rnd.random() < 0.5
    if kind == 1:
        return rnd.randint(-(10**30), 10**30)
    if kind == 2:
        return rnd.choice([rnd.uniform(-1e300, 1e300), float("inf"), -0.0, 5e-324])
    return "".join(rnd.choice(PIECES) for _ in range(rnd.randint(0, 8)))


def test_any_config_built_in_code_reads_back_as_itself() -> None:
    rnd = random.Random(SEED + 1)
    for _ in range(1500):
        config = Config()
        for _ in range(rnd.randint(0, 6)):
            section = rnd.choice(["", "A", " B ", "a]b", "[x", "Sec 1"])
            key = rnd.choice(["k", "Key Name", "x.y", "[k", "k]", "\u00e9"])
            try:
                config.set(section, key, _value(rnd))
            except LvConfigError:
                continue
        try:
            text = dump(config)
        except LvConfigError:
            continue
        again = parse(text)
        assert again == config
        assert dump(again) == text


def test_escape_round_trips_every_string() -> None:
    rnd = random.Random(SEED + 2)
    for _ in range(5000):
        text = "".join(
            chr(rnd.randrange(0x110000 if rnd.random() < 0.1 else 0x100))
            for _ in range(rnd.randint(0, 20))
        )
        text = text.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
        assert unescape(escape(text)) == text


def test_typed_readers_only_raise_their_documented_errors() -> None:
    rnd = random.Random(SEED + 3)
    for _ in range(5000):
        text = _text(rnd, 12)
        for call in (to_bool, to_int, to_float):
            with contextlib.suppress(LvConfigError):
                call(text)
        for path_call in (to_labview_path, from_labview_path):
            with contextlib.suppress(LvPathError):
                path_call(text)


@pytest.mark.parametrize(
    "build",
    [
        lambda n: "[A]\n" + "k = v\n" * n,
        lambda n: "[A]\nk = " + "\\" * n + "\n",
        lambda n: "[A]\nk = " + "\\0A" * n + "\n",
        lambda n: "[" * n + "]\n",
        lambda n: "".join(f"[S{i}]\nk{i} = {i}\n" for i in range(n // 8)),
        lambda n: "[A]\n" + "k = 1\n" * n,  # one key repeated n times
    ],
)
def test_parse_and_dump_scale_linearly(build: object) -> None:
    assert callable(build)

    def cost(n: int) -> float:
        text = build(n)
        start = time.perf_counter()
        config = parse(text)
        dump(config)
        dump(config, normalize=True)
        return time.perf_counter() - start

    cost(1000)
    small, large = min(cost(20000) for _ in range(3)), min(cost(160000) for _ in range(3))
    assert large < small * 8 * 4  # 8 times the input, well under quadratic


def test_long_numbers_and_paths_stay_fast() -> None:
    start = time.perf_counter()
    with pytest.raises(LvConfigError):
        to_int("9" * 100000)
    assert to_float("1" * 100000) == float("inf")
    assert from_labview_path("/C" + "/a" * 100000).count("\\") == 100000
    assert time.perf_counter() - start < 5
