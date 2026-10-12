"""Command-line interface: inspect, edit and convert LabVIEW configuration files."""

from __future__ import annotations

import argparse
import configparser
import io
import sys
from collections.abc import Sequence
from typing import NoReturn

from . import _commands
from ._errors import LvConfigError

_EPILOG = """\
examples:
  lvconfig json settings.ini                      # every section as decoded JSON
  lvconfig json settings.ini --section General    # one section only
  lvconfig get settings.ini General enabled --type bool
  lvconfig get settings.ini Paths log --type path # prints C:\\Temp\\log.txt
  lvconfig set settings.ini General retries 5     # edit in place, nothing else moves
  lvconfig set settings.ini Paths log "D:\\logs\\run.txt" --type path
  lvconfig fmt settings.ini -o tidy.ini           # canonical LabVIEW form
  lvconfig convert plain.ini labview.ini          # plain .ini to LabVIEW form

Errors go to stderr with exit status 1.
"""

_SET_HELP = """\
how to store VALUE: auto keeps the existing key's quoting (bare tokens stay bare,
new keys become quoted strings), str quotes and escapes, bool writes TRUE/FALSE,
int/float a bare number, path the LabVIEW stored form (default: auto)"""


_POSIX_HELP = "with --type path: use POSIX paths instead of Windows ones"


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _build_parser() -> argparse.ArgumentParser:
    from . import __version__

    parser = _Parser(
        prog="lvconfig",
        description="Read, edit, inspect and convert LabVIEW configuration (.ini) files.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvconfig {__version__}")
    parser.add_argument("--encoding", default="utf-8", help="file encoding (default: utf-8)")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p = sub.add_parser("json", help="print a LabVIEW .ini as decoded JSON")
    p.add_argument("file", help="LabVIEW .ini file")
    p.add_argument("--section", help="limit the output to one section")
    p.set_defaults(func=_commands.cmd_json)

    p = sub.add_parser("get", help="print one decoded value")
    p.add_argument("file", help="LabVIEW .ini file")
    p.add_argument("section", help='section name ("" for keys before any section)')
    p.add_argument("key")
    p.add_argument(
        "--type",
        choices=["str", "bool", "int", "float", "path"],
        default="str",
        help="how to read the value (default: str)",
    )
    p.add_argument("--posix", action="store_true", help=_POSIX_HELP)
    p.set_defaults(func=_commands.cmd_get)

    p = sub.add_parser("set", help="set one value, keeping every other byte of the file")
    p.add_argument("file", help="LabVIEW .ini file, rewritten in place")
    p.add_argument("section")
    p.add_argument("key")
    p.add_argument("value")
    p.add_argument(
        "--type",
        choices=["auto", "str", "bool", "int", "float", "path"],
        default="auto",
        help=_SET_HELP,
    )
    p.add_argument("--posix", action="store_true", help=_POSIX_HELP)
    p.add_argument("-o", "--output", help="write here instead of rewriting FILE")
    p.set_defaults(func=_commands.cmd_set)

    p = sub.add_parser("fmt", help="rewrite a LabVIEW .ini in canonical form")
    p.add_argument("file", help="LabVIEW .ini file")
    p.add_argument("-o", "--output", help="output file with CRLF endings (default: stdout)")
    p.set_defaults(func=_commands.cmd_fmt)

    p = sub.add_parser("convert", help="convert a plain .ini to LabVIEW form")
    p.add_argument("input", help="plain .ini file, as configparser writes it")
    p.add_argument("output", nargs="?", help="output file with CRLF endings (default: stdout)")
    p.set_defaults(func=_commands.cmd_convert)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface and return a process exit code."""
    # Values may hold any character; a Windows pipe defaults to a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    args = _build_parser().parse_args(argv)
    try:
        exit_code: int = args.func(args)
        return exit_code
    except (LvConfigError, OSError, ValueError, configparser.Error) as exc:
        print(f"lvconfig: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
