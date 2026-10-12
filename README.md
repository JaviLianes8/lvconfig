# lvconfig

Typed reader and writer for LabVIEW configuration files, with LabVIEW-correct escaping, path and boolean rules.

## Install

```
pip install lvconfig
```

## Usage

```python
import lvconfig

text = """
; rig configuration
[General]
name = "Rig \\22A\\22"
enabled = TRUE
retries = 3

[Paths]
log = "/C/Temp/log.txt"
"""

config = lvconfig.parse(text)

config.get_str("General", "name")  # 'Rig "A"' (quotes decoded from \22)
config.get_bool("General", "enabled")  # True
config.get_int("General", "retries")  # 3
config.get_path("Paths", "log")  # 'C:\\Temp\\log.txt'

# Build and write a file LabVIEW reads back correctly.
out = lvconfig.Config()
out.set("General", "name", 'Rig "A"\r')  # quoted and escaped on dump
out.set("General", "enabled", True)  # written as TRUE, not "True"
out.set_path("Paths", "log", r"C:\Temp\log.txt")  # stored as /C/Temp/log.txt
print(lvconfig.dump(out))
```

## Editing a file without disturbing it

`dump(parse(text))` returns `text` unchanged, byte for byte. `parse` records the source
layout: blank lines, `;` and `#` comments, `key = value` spacing, `CRLF` or `LF` line
endings, a missing final newline, repeated sections and a UTF-8 byte order mark. `dump`
writes every untouched line back verbatim and rewrites only what you changed:

```python
config = lvconfig.load("settings.ini")
config.set("General", "retries", 5)  # only this line changes, spacing kept
config.remove("General", "obsolete")  # the key goes, with its comment lines
config.set("New", "enabled", False)  # new sections are appended at the end
lvconfig.save(config, "settings.ini")
```

`load` and `save` keep the file's own line endings. A config built in code is saved
with the `CRLF` endings LabVIEW writes on Windows, and `save(..., line_ending="\n")`
forces one terminator everywhere. `dump(config, normalize=True)` writes the canonical
form instead: `key=value` with no spaces, one blank line between sections.

Comments are also exposed for reading and editing: `Entry.comments`,
`Config.header_comments` and `Config.trailing_comments`. Replacing a value with `set`
keeps the comments above it. A repeated key keeps its last value, and keys found before
the first section header live in the section named `""`. `Config` also offers `items`,
`to_dict`, `remove` and `remove_section`.

This is checked against real files: the test suite carries verbatim excerpts of
configuration files installed with LabVIEW 2026 (`tests/fixtures/labview2026/`, with
their source paths) and round-trips each one byte for byte. When LabVIEW is installed
locally, it also round-trips every `.ini` file of the installation.

Low-level helpers are public too: `escape`/`unescape` for the `\XX` codes,
`to_labview_path`/`from_labview_path` for the stored path form, and
`to_bool`/`to_int`/`to_float` for value coercion.

## Paths

| Native (Windows)                 | Stored                           |
| -------------------------------- | -------------------------------- |
| `C:\Program Files (x86)\Arduino` | `/C/Program Files (x86)/Arduino` |
| `D:\`                            | `/D`                             |
| `\\server\share\dir`             | `//server/share/dir`             |
| `..\Builds\app.vi`               | `../Builds/app.vi`               |
| empty (not a path)               | empty                            |

- The drive letter keeps its case. Forward slashes are accepted in Windows input.
- A value already in native Windows form (`c:\NI Installers`), which some NI files
  store, is read as is on Windows.
- `get_path(..., windows=False)` returns the stored text unchanged, which is already a
  POSIX path.
- A path with no faithful stored form raises `LvPathError` (a `ValueError`) instead of
  being rewritten into a path to a different file: a drive-relative `C:file` or bare
  `C:`, a rooted path without a drive (`\dir`), a UNC path without a share and a
  `\\?\` device path. On Windows, reading a POSIX absolute value such as `/usr/lib`
  raises too. These are the same rules as the sibling `lvpath` library.

## Command line

Installing the package puts an `lvconfig` command on the path:

```
lvconfig json settings.ini                      # every section as decoded JSON
lvconfig json settings.ini --section General    # one section only
lvconfig get settings.ini General enabled --type bool
lvconfig get settings.ini Paths log --type path # prints C:\Temp\log.txt
lvconfig set settings.ini General retries 5     # edit in place, nothing else moves
lvconfig set settings.ini Paths log "D:\logs\run.txt" --type path
lvconfig fmt settings.ini -o tidy.ini           # canonical LabVIEW form
lvconfig convert plain.ini labview.ini          # plain .ini to LabVIEW form
```

`set` keeps the existing key's quoting unless `--type` says otherwise, and `-o` writes
the result elsewhere. `convert` reads a plain INI (the kind `configparser` writes),
infers booleans and numbers, and writes it with LabVIEW escaping, quoting and path
form. Errors, including usage errors, go to stderr with exit status 1. Run
`lvconfig --help` for the full list.

## Escaping rules it handles

- `\XX` hex codes for control and non-displayable characters (a carriage return is
  `\0D`, a tab is `\09`), decoded on read and re-encoded on write with uppercase digits.
- Doubled backslashes: a literal backslash is stored as `\\`.
- Quoted strings: string and path values are wrapped in double quotes to protect
  surrounding whitespace, and the quotes come off on read.
- Stored paths: see [Paths](#paths).
- Booleans as `TRUE`/`FALSE` on write; `TRUE`, `True`, `true` and `1` (and their false
  counterparts) on read, all of which LabVIEW's own files use.
- Special numbers as `Inf`, `-Inf` and `NaN`.

## Why

LabVIEW's "Configuration File" format looks like an INI file but is not one. LabVIEW's
own Configuration File VIs, and the OpenG Variant Configuration File library on top of them,
encode control characters as `\XX` hex codes (a carriage
return is `\0D`), double literal backslashes, wrap string and path values in quotation
marks to protect whitespace, store paths in a platform-neutral form with the drive
after a leading slash (`C:\Temp` becomes `/C/Temp`), and write booleans as `TRUE` or
`FALSE`. These rules are described in NI's [Windows configuration settings file
format](https://www.ni.com/docs/en-US/bundle/labview/page/windows-configuration-settings-file-format.html)
documentation. All of that runs inside LabVIEW; none of it helps a Python process with no
LabVIEW present.

Python's standard-library `configparser` honours none of them: it does not decode
`\XX` escapes, treats backslashes literally, keeps the surrounding quotation marks as
part of the value, and leaves `/C/Temp` as a broken path. The result is a corrupted
read and a file LabVIEW cannot load back. This is a long-standing pain point in the NI
community (for example the "ConfigFile Read Key" doubled-backslash reports on
forums.ni.com), and at the time of writing no maintained PyPI package implements these
semantics: the available INI parsers (`configparser`, `iniparse`, `iniparser2`) are all
generic and share the same gap.

`lvconfig` reads and writes the format exactly as LabVIEW does, round-trips losslessly,
and coerces each value to the Python type it stands for. It is pure standard library,
fully typed, and ships `py.typed`.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
