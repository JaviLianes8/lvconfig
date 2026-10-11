"""Command-line interface: inspect and convert LabVIEW configuration files."""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from collections.abc import Sequence

from ._config import Config
from ._dump import dump
from ._errors import LvConfigError
from ._io import load, save

_EPILOG = """\
examples:
  lvconfig json settings.ini
  lvconfig json settings.ini --section General
  lvconfig get settings.ini General enabled --type bool
  lvconfig get settings.ini Paths log --type path
  lvconfig convert plain.ini labview.ini
"""


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


def _cmd_json(args: argparse.Namespace) -> int:
    config = load(args.file, encoding=args.encoding)
    data = config.to_dict()
    if args.section is not None:
        data = {args.section: data.get(args.section, {})}
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def _cmd_get(args: argparse.Namespace) -> int:
    config = load(args.file, encoding=args.encoding)
    readers = {
        "str": config.get_str,
        "bool": config.get_bool,
        "int": config.get_int,
        "float": config.get_float,
        "path": config.get_path,
    }
    print(readers[args.type](args.section, args.key))
    return 0


def _cmd_convert(args: argparse.Namespace) -> int:
    with open(args.input, encoding=args.encoding) as handle:
        config = _plain_to_config(handle.read())
    if args.output is None:
        sys.stdout.write(dump(config))
    else:
        save(config, args.output, encoding=args.encoding)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    from . import __version__

    parser = argparse.ArgumentParser(
        prog="lvconfig",
        description="Read, inspect and convert LabVIEW configuration (.ini) files.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvconfig {__version__}")
    parser.add_argument("--encoding", default="utf-8", help="file encoding (default: utf-8)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_json = subparsers.add_parser("json", help="dump a LabVIEW .ini as decoded JSON")
    p_json.add_argument("file", help="path to the LabVIEW .ini file")
    p_json.add_argument("--section", help="limit the output to a single section")
    p_json.set_defaults(func=_cmd_json)

    p_get = subparsers.add_parser("get", help="print one decoded value")
    p_get.add_argument("file", help="path to the LabVIEW .ini file")
    p_get.add_argument("section")
    p_get.add_argument("key")
    p_get.add_argument(
        "--type",
        choices=["str", "bool", "int", "float", "path"],
        default="str",
        help="how to coerce the value (default: str)",
    )
    p_get.set_defaults(func=_cmd_get)

    p_conv = subparsers.add_parser("convert", help="convert a plain .ini to LabVIEW form")
    p_conv.add_argument("input", help="path to the plain .ini file")
    p_conv.add_argument("output", nargs="?", help="output file (default: stdout)")
    p_conv.set_defaults(func=_cmd_convert)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code: int = args.func(args)
        return exit_code
    except (LvConfigError, KeyError, OSError, configparser.Error) as exc:
        print(f"lvconfig: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
