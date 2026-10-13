# lvconfig

Typed reader and writer for LabVIEW configuration files, with LabVIEW-correct escaping, path and boolean rules.

LabVIEW's Configuration File VIs write files that look like INI files but follow their own
rules: control characters become `\XX` codes, backslashes are doubled, strings and paths
are quoted, paths are stored as `/C/Temp/log.txt`, booleans are `TRUE` and `FALSE`, and
numbers follow the system's decimal separator. `lvconfig` reads and writes those files from
Python exactly as LabVIEW 2026 does, edits them without disturbing a single other byte, and
turns each value into the Python type it stands for. It is pure standard library, typed,
and has no dependencies.

## Install

```
pip install lvconfig
```

Python 3.10 or newer.

## Quick start

```pycon
>>> import lvconfig
>>> text = (
...     '[Rig]\r\nname = "Bench\\0A2"\r\nenabled = TRUE\r\ngain = 2,500000\r\nlog = "/C/Temp/log.txt"'
... )
>>> config = lvconfig.parse(text)
>>> config.get_str("Rig", "name")
'Bench\n2'
>>> config.get_bool("Rig", "enabled"), config.get_float("Rig", "gain")
(True, 2.5)
>>> print(config.get_path("Rig", "log"))
C:\Temp\log.txt
>>> config.set("Rig", "gain", 3.0)
>>> print(lvconfig.dump(config).replace("\r\n", "\n"))
[Rig]
name = "Bench\0A2"
enabled = TRUE
gain = 3.0
log = "/C/Temp/log.txt"

```

Only the `gain` line changed; every other byte, the `CRLF` endings included, is the
original text. `lvconfig.load` and `lvconfig.save` do the same with files.

Building a file from scratch gives the layout LabVIEW writes itself:

```pycon
>>> out = lvconfig.Config()
>>> out.set("Rig", "name", 'Bench "A"')
>>> out.set("Rig", "enabled", True)
>>> out.set_path("Rig", "log", r"C:\Temp\log.txt")
>>> print(lvconfig.dump(out))
[Rig]
name = "Bench "A""
enabled = TRUE
log = "/C/Temp/log.txt"

```

## What it gets right

Every rule below was checked against files LabVIEW 2026 wrote and values it read back
(the captures ship with the tests, in `tests/fixtures/labview2026/`):

- Escapes: a backslash is doubled and the control characters below 0x20, except tab, are
  written as `\XX`. On read only `\00` to `\1F` in upper case are codes; `\22` or `\0a`
  stay as text, as LabVIEW leaves them.
- Quoted and bare values are both unescaped; spaces and tabs around a value are trimmed,
  nothing else.
- A repeated key reads as its first line, the one LabVIEW sees, and names that differ only
  in case count as repeats. New keys go into the block of a section LabVIEW reads.
- A `;` in a bare value starts a comment, read the way LabVIEW reads it; the typed getters
  stop at it (`TRUE ; note` is `True`).
- Booleans: `TRUE`, `yes`, `on`, `t`, `y`, `1` and `FALSE`, `no`, `off`, `f`, `0`, in any case.
- Numbers: `2,5` and `2.5` both read as 2.5 (LabVIEW writes `2,500000` on a system whose
  decimal separator is a comma); `Inf`, `-Inf` and `NaN`.
- Paths: `/C/a//b/./c/../d` reads as `C:\a\b\d`, `a/./b/../c` as `a\c`, a UNC path as
  `//server/share`.
- Where LabVIEW quietly reads part of a value (`12abc` as 12, `1_000` as 1) or a path that
  names another file (`/usr/lib` as `u:\sr\lib`), lvconfig raises instead of guessing.

## Command line

```
lvconfig json settings.ini                      # every section as decoded JSON
lvconfig get settings.ini Rig enabled --type bool
lvconfig set settings.ini Rig retries 5         # edit in place, nothing else moves
lvconfig fmt settings.ini -o tidy.ini           # the layout LabVIEW writes
lvconfig convert plain.ini labview.ini          # plain .ini to LabVIEW form
```

Errors go to stderr with exit status 1. `lvconfig --help` lists every option.

## Why

Python's `configparser` reads such a file wrongly: it keeps the quotes as part of a value,
leaves `\0A` and doubled backslashes undecoded, returns `/C/Temp/log.txt` as it is stored,
lower-cases key names, and drops every comment when it writes the file back. lvconfig
follows LabVIEW's rules, checked against LabVIEW's own output, and changes only the lines
you edit.

## Documentation

- [Guide](https://github.com/JaviLianes8/lvconfig/blob/main/GUIDE.md): every rule, the
  error types, the command line and the upgrade notes from 0.3.
- [Changelog](https://github.com/JaviLianes8/lvconfig/blob/main/CHANGELOG.md)

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvconfig/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
