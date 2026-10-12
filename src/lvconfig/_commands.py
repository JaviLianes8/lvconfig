"""The work behind each ``lvconfig`` sub-command."""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from collections.abc import Callable

from ._coerce import to_bool, to_float, to_int
from ._config import Config, Entry
from ._dump import dump
from ._errors import LvConfigError
from ._io import load, save


def _infer(value: str) -> str | bool | int | float:
    token = value.strip()
    low = token.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return value


def _plain_to_config(text: str) -> Config:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # type: ignore[method-assign,assignment]
    parser.read_string(text)
    config = Config()
    for section in parser.sections():
        for key, value in parser.items(section):
            config.set(section, key, _infer(value))
    return config


def _require(config: Config, section: str, key: str | None = None) -> None:
    if section not in config.sections:
        raise LvConfigError(f"no section {section!r}")
    if key is not None and not config.has(section, key):
        raise LvConfigError(f"no key {key!r} in section {section!r}")


def cmd_json(args: argparse.Namespace) -> int:
    config = load(args.file, encoding=args.encoding)
    data = config.to_dict()
    if args.section is not None:
        _require(config, args.section)
        data = {args.section: data[args.section]}
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    config = load(args.file, encoding=args.encoding)
    _require(config, args.section, args.key)
    readers = {
        "str": config.get_str,
        "bool": config.get_bool,
        "int": config.get_int,
        "float": config.get_float,
        "path": config.get_path,
    }
    value = readers[args.type](args.section, args.key)
    print(value)
    return 0


def _bare_ok(value: str) -> bool:
    # A bare token cannot be escaped, so it must be printable and carry no edge spaces.
    return value == value.strip() and all(" " <= char != "\x7f" for char in value)


def _store(config: Config, args: argparse.Namespace) -> None:
    section, key, value = args.section, args.key, args.value
    if args.type == "auto":
        old = config.sections.get(section, {}).get(key)
        if old is not None and not old.quoted and _bare_ok(value):
            config.sections[section][key] = Entry(value, False, old.comments)
        else:
            config.set(section, key, value)
    elif args.type == "path":
        config.set_path(section, key, value)
    else:
        coerce: dict[str, Callable[[str], str | bool | int | float]] = {
            "str": str,
            "bool": to_bool,
            "int": to_int,
            "float": to_float,
        }
        config.set(section, key, coerce[args.type](value))


def cmd_set(args: argparse.Namespace) -> int:
    config = load(args.file, encoding=args.encoding)
    _store(config, args)
    save(config, args.output or args.file, encoding=args.encoding)
    return 0


def _emit(text: str, output: str | None, encoding: str) -> None:
    if output is None:
        sys.stdout.write(text)
        return
    with open(output, "w", encoding=encoding, newline="") as handle:
        handle.write(text.replace("\n", "\r\n"))


def cmd_fmt(args: argparse.Namespace) -> int:
    config = load(args.file, encoding=args.encoding)
    _emit(dump(config, normalize=True), args.output, args.encoding)
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    with open(args.input, encoding=args.encoding) as handle:
        config = _plain_to_config(handle.read())
    _emit(dump(config), args.output, args.encoding)
    return 0
