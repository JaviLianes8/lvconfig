"""One test per public name, pinning the whole promise its docstring makes."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

import lvconfig
from lvconfig import (
    Config,
    Entry,
    LvConfigError,
    LvParseError,
    LvPathError,
    dump,
    escape,
    from_labview_path,
    load,
    parse,
    save,
    to_bool,
    to_float,
    to_int,
    to_labview_path,
    unescape,
)


def test_error_hierarchy_promise() -> None:
    assert issubclass(LvParseError, LvConfigError) and issubclass(LvPathError, LvConfigError)
    assert issubclass(LvPathError, ValueError) and not issubclass(LvParseError, ValueError)
    error = LvParseError("bad", 7)
    assert (str(error), error.line) == ("line 7: bad", 7)


def test_entry_promise() -> None:
    entry = Entry("x", quoted=True, comments=("; c",))
    assert (entry.value, entry.quoted, entry.comments) == ("x", True, ("; c",))
    assert Entry("x", True) == Entry("x", True, ())
    with pytest.raises(AttributeError):
        entry.value = "y"  # type: ignore[misc]


def test_escape_and_unescape_promise() -> None:
    every = "".join(chr(code) for code in range(256))
    stored = escape(every)
    assert unescape(stored) == every
    assert stored.count("\\") == 31 + 2  # 31 codes below 0x20 (tab kept) and one doubled
    assert escape(every, raw=True) == every


def test_parse_and_dump_promise() -> None:
    text = '; top\r\n[A]\r\n  name = "Rig\\09A"  \r\nn=1\r\nn=2\r\nbare=a\\0Ab\r\n'
    config = parse(text)
    assert dump(config) == text
    assert config.to_dict() == {"A": {"name": "Rig\tA", "n": "1", "bare": "a\nb"}}
    assert config.header_comments == {"A": ("; top",)}
    assert parse(dump(config, normalize=True)) == config


def test_config_write_promise() -> None:
    config = Config()
    config.set("A", "s", "text")
    config.set("A", "b", False)
    config.set("A", "i", -3)
    config.set("A", "f", 0.1)
    config.set("A", "nan", math.nan)
    config.set_path("A", "p", "C:\\x")
    assert config.items("A") == [
        ("s", "text"),
        ("b", "FALSE"),
        ("i", "-3"),
        ("f", "0.1"),
        ("nan", "NaN"),
        ("p", "/C/x"),
    ]
    assert [config.sections["A"][k].quoted for k in config.keys("A")] == [
        True,
        False,
        False,
        False,
        False,
        True,
    ]
    assert config.has("A", "s") and not config.has("A", "S") and not config.has("B", "s")
    assert config.remove("A", "s") and not config.remove("A", "s")
    assert config.remove_section("A") and config.section_names() == []


def test_config_read_promise() -> None:
    config = parse("[A]\ns=x\nb=yes\ni=+7\nf=2,5\np=/D/data\n")
    assert config.get("A", "s") == config.get_str("A", "s") == "x"
    assert config.get("A", "zz", "d") == "d" and config.get("Z", "s") is None
    assert config.get_bool("A", "b") is True and config.get_int("A", "i") == 7
    assert config.get_float("A", "f") == 2.5
    assert config.get_path("A", "p") == "D:\\data"
    assert config.get_path("A", "p", windows=False) == "/D/data"
    with pytest.raises(KeyError):
        config.get_str("A", "missing")


def test_coercion_promise() -> None:
    assert [to_bool(t) for t in ("TRUE", "yes", "On", "t", "Y", "1")] == [True] * 6
    assert [to_bool(t) for t in ("false", "NO", "off", "F", "0")] == [False] * 5
    assert to_int("\t-0012 ") == -12 and to_float("1e3") == 1000.0
    assert to_float(",5") == 0.5 and math.isinf(to_float("INFINITY"))
    for call, text in [(to_bool, "n"), (to_int, "1_000"), (to_float, "12abc")]:
        with pytest.raises(LvConfigError):
            call(text)


def test_path_promise() -> None:
    assert to_labview_path("D:\\") == "/D"
    assert from_labview_path("/D") == "D:\\"
    assert from_labview_path(to_labview_path("\\\\srv\\share\\a b")) == "\\\\srv\\share\\a b"
    assert (
        to_labview_path("rel\\x.vi") == "rel/x.vi" == from_labview_path("rel/x.vi", windows=False)
    )
    for bad in ("C:x", "\\dir", "\\\\srv", "\\\\?\\C:\\x"):
        with pytest.raises(LvPathError):
            to_labview_path(bad)
    for bad in ("/usr/lib", "/C:/x", "/C/..", "\\\\srv\\share"):
        with pytest.raises(LvPathError):
            from_labview_path(bad)


def test_load_and_save_promise(tmp_path: Path) -> None:
    target = tmp_path / "a.ini"
    config = Config()
    config.set("A", "x", "\u00e9")
    save(config, target, encoding="cp1252")
    assert target.read_bytes() == b'[A]\r\nx = "\xe9"'
    loaded = load(target, encoding="cp1252")
    assert loaded == config
    loaded.set("A", "y", 1)
    save(loaded, target, encoding="cp1252", line_ending="\n")
    assert target.read_bytes() == b'[A]\nx = "\xe9"\ny = 1'


def test_version_promise() -> None:
    assert lvconfig.__version__ == "1.0.0"
