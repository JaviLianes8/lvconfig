# lvconfig guide

This guide is the reference for lvconfig 1.0. Every example on this page runs as part of
the test suite. The behaviour it describes was checked against LabVIEW 2026 Community
(26.3.1f1, Windows): the files LabVIEW wrote and the values it read are kept in
`tests/fixtures/labview2026/`, and the tests compare lvconfig with them case by case.

## The model

`parse(text)` and `load(path)` return a `Config`:

- `Config.sections` maps each section name to a dictionary of `Entry` objects, in file order.
  Keys found before the first `[section]` header live in the section named `""`.
- `Entry(value, quoted, comments)` holds the decoded text of one value, whether it was
  written in quotes, and the comment lines just above its key.
- `Config.header_comments` holds the comment lines above each section header and
  `Config.trailing_comments` those after the last key.
- `Config.layout` records the source text, so `dump` can write back every untouched line
  byte for byte. It takes no part in equality.

```pycon
>>> from lvconfig import Config, Entry, dump, parse
>>> config = parse('; rig settings\n[Rig]\n; how many tries\nretries = 3\nname = "Bench"\n')
>>> config.sections["Rig"]["retries"]
Entry(value='3', quoted=False, comments=('; how many tries',))
>>> config.header_comments
{'Rig': ('; rig settings',)}

```

## Reading values

| Text in the file | What lvconfig reads | Rule |
| --- | --- | --- |
| `name = "  pad  "` | `'  pad  '` | quotes come off; what is inside them is kept |
| `name =   x y   ` | `'x y'` | spaces and tabs around a value are trimmed, nothing else |
| `name = 'sq'` | `'sq'` | single quotes come off too |
| `name = "a\09b\\c"` | `'a\tb\\c'` | `\\` is one backslash, `\00` to `\1F` are control characters |
| `name = a\0Ab` | `'a\nb'` | bare values are unescaped as well |
| `name = "a\22b\0a"` | `'a\\22b\\0a'` | any other backslash is text, as LabVIEW reads it |
| `x = 1` then `x = 2` | `'1'` | the first line of a repeated key wins; the second stays in the text |

```pycon
>>> config = parse('[S]\nq = "a\\09b\\\\c"\nbare = a\\0Ab\nx = 1\nx = 2\n')
>>> config.get_str("S", "q"), config.get_str("S", "bare"), config.get_str("S", "x")
('a\tb\\c', 'a\nb', '1')

```

### Typed reads

| Getter | Accepts | Refuses (LabVIEW reads it partly or returns its default) |
| --- | --- | --- |
| `get_bool`, `to_bool` | `TRUE`, `yes`, `on`, `t`, `y`, `1`; `FALSE`, `no`, `off`, `f`, `0`; any case | `n`, `2`, `enabled`, empty |
| `get_int`, `to_int` | optional sign and ASCII digits: `-12`, `007` | `12abc`, `3.7`, `1_000`, `0x10`, `1e3` |
| `get_float`, `to_float` | `2.5`, `2,5`, `,5`, `5.`, `1e3`, `Inf`, `-Infinity`, `NaN` | `12abc`, `1_000`, `1,234,5`, `0x10`, `-NaN` |
| `get_path` | see [Paths](#paths) | paths with no faithful native form |

LabVIEW's Read Key (I32) clamps to 32 bits; `get_int` returns the full Python integer.

```pycon
>>> from lvconfig import LvConfigError, to_bool, to_float, to_int
>>> to_bool(" Yes "), to_int("-007"), to_float("2,500000")
(True, -7, 2.5)
>>> try:
...     to_int("12abc")
... except LvConfigError as error:
...     print(error)
not an integer: '12abc'

```

## Writing values

`Config.set` infers how LabVIEW stores a Python value:

| Python value | Stored as |
| --- | --- |
| `True`, `False` | `TRUE`, `FALSE` |
| `int` | its decimal digits, bare |
| `float` | Python's shortest round-trip form with `.`, bare; `Inf`, `-Inf`, `NaN` |
| `str` | quoted and escaped |
| a path, through `set_path` | the stored form, quoted |

Escaping follows LabVIEW's writer exactly: a backslash is doubled, control characters below
0x20 except tab become `\XX` in upper case, and everything else, the double quote included,
is written as it is. A value with a `;`, edge blanks or surrounding quotes is never written
bare, because LabVIEW would read it differently.

```pycon
>>> from lvconfig import escape, unescape
>>> print(escape('C:\\data "x"\r\n'))
C:\\data "x"\0D\0A
>>> escape("tab\tkept")
'tab\tkept'
>>> unescape(escape('C:\\data\t"x"\r\n')) == 'C:\\data\t"x"\r\n'
True

```

## Paths

| Stored | Native (Windows) |
| --- | --- |
| `/C/Temp/log.txt` | `C:\Temp\log.txt` |
| `/D` or `/D/` | `D:\` |
| `//server/share/dir` | `\\server\share\dir` |
| `../Builds/app.vi` | `..\Builds\app.vi` |
| `/C/a//b/./c/../d/` | `C:\a\b\d` |
| `C:\NI Installers` (native form, as some NI files store it) | `C:\NI Installers` |

`to_labview_path` and `set_path` go the other way. Pass `windows=False` (or `--posix` on
the command line) for POSIX paths, which are already in stored form.

A path that has no faithful counterpart raises `LvPathError` instead of turning into a
path to another file: a drive-relative `C:file` or bare `C:`, a rooted path without a drive
(`\dir`, `/dir`), a UNC path without a share, a `\\?\` device path, a POSIX absolute value
such as `/usr/lib` read as Windows (LabVIEW reads it as `u:\sr\lib`), a malformed `/C:/x`,
a `..` above the drive root, and a UNC path stored with backslashes.

```pycon
>>> from lvconfig import LvPathError, from_labview_path, to_labview_path
>>> print(from_labview_path("/C/a//b/./c/../d/"))
C:\a\b\d
>>> to_labview_path(r"\\server\share\dir")
'//server/share/dir'
>>> try:
...     to_labview_path("C:file")
... except LvPathError as error:
...     print(error)
'C:file' is drive-relative and has no stored form

```

## Editing files

`dump(parse(text)) == text` for every text `parse` accepts. Blank lines, `;` and `#`
comments, `key = value` spacing, `CRLF`, `LF` or `CR` endings, a missing final newline,
repeated sections and a UTF-8 byte order mark all survive. After an edit:

- an edited key is rewritten in place, keeping its `key = ` spacing and line ending;
- a removed key or section disappears with its comment lines, and a removed key takes its
  repeated lines along, so no older value comes back;
- a new key goes after the last line of its section, a new section at the end of the file;
- edited comments are written where the old ones were.

```pycon
>>> config = parse("[A]\r\n  x   =  1\r\n; old\r\ny=2")
>>> config.set("A", "x", 5)
>>> config.remove("A", "y")
True
>>> config.set("B", "on", True)
>>> dump(config)
'[A]\r\n  x   =  5\r\n\r\n[B]\r\non = TRUE'

```

### The canonical form

A config built in code, or `dump(config, normalize=True)`, is written in the layout of
LabVIEW's own Configuration File VIs: `key = value`, a blank line before each section
header, comments above their section or key, and no newline after the last line. `dump`
separates lines with `\n`; `save` writes LabVIEW's `\r\n` for a config built in code. For a
file without comments or repeated keys, this is byte for byte the file LabVIEW writes after
the same change.

```pycon
>>> print(dump(parse("[A]\n\n\n  x=1  \n[B]\ny  =  'v'\n"), normalize=True))
[A]
x = 1
<BLANKLINE>
[B]
y = "v"

```

## Files and encodings

`load(path, encoding="utf-8")` reads without newline translation, and `save(config, path,
encoding="utf-8", line_ending=None)` keeps the endings a file was read with. LabVIEW writes
in the system code page, so pass `encoding="cp1252"` (or your system's) for a file with
text beyond ASCII. `line_ending` may force `"\r\n"`, `"\n"` or `"\r"` on every line. The text
is rendered before the file is opened, so a refused config leaves the file untouched.

## Errors

| Error | Raised by | When |
| --- | --- | --- |
| `LvParseError` (an `LvConfigError`, with `.line`) | `parse`, `load` | a line that is not a section, key or comment |
| `LvConfigError` | `to_bool`, `to_int`, `to_float` and the getters | text that is not that type |
| `LvConfigError` | `set`, `dump`, `save` | a key with `=`, a line break or edge blanks, a key starting with `;` or `#`, a section name with a line break, a bare value LabVIEW would read differently, a comment that is not a comment, header comments for a missing section |
| `LvPathError` (an `LvConfigError` and a `ValueError`) | the path functions, `set_path`, `get_path` | a path with no faithful counterpart |
| `KeyError` | `get_str` and the typed getters | a missing section or key (`get` returns a default instead) |
| `TypeError` | every function | an argument of the wrong type |
| `ValueError` | `save` | a `line_ending` other than `None`, CRLF, LF or CR |

Messages quote at most 40 characters of the offending text, so a huge value never floods a
log.

## Where lvconfig and LabVIEW differ

These are deliberate, and each is pinned by a test against LabVIEW's own reading:

- LabVIEW matches section and key names without regard to case; lvconfig matches them
  exactly.
- LabVIEW sees only the first block of a repeated section and nothing before the first
  header; lvconfig merges repeated sections and keeps headerless keys in the section `""`.
- LabVIEW reads a line with no `=` as a key with an empty value; `parse` raises
  `LvParseError` for it.
- LabVIEW treats `;` inside a bare value as the start of a comment and returns a rejoined
  text; lvconfig keeps the value as written, and always quotes a value with `;` when it
  writes one.
- LabVIEW reads the leading part of `12abc`, `1_000` or `0x10` as a number, and clamps
  integers to 32 bits; lvconfig refuses partial numbers and keeps every digit.

## Command line

Installing the package puts an `lvconfig` command on the path. Given this file:

```pycon
>>> from lvconfig import save
>>> settings = Config()
>>> settings.set("Rig", "enabled", True)
>>> settings.set("Rig", "retries", 3)
>>> settings.set_path("Rig", "log", r"C:\Temp\log.txt")
>>> save(settings, "settings.ini")

```

```
$ lvconfig get settings.ini Rig enabled --type bool
True
$ lvconfig get settings.ini Rig log --type path
C:\Temp\log.txt
$ lvconfig set settings.ini Rig retries 5
$ lvconfig get settings.ini Rig retries --type int
5
$ lvconfig json settings.ini --section Rig
{
  "Rig": {
    "enabled": "TRUE",
    "retries": "5",
    "log": "/C/Temp/log.txt"
  }
}
```

| Command | Does |
| --- | --- |
| `json FILE [--section S]` | prints the decoded values as JSON |
| `get FILE SECTION KEY [--type str/bool/int/float/path] [--posix]` | prints one value |
| `set FILE SECTION KEY VALUE [--type auto/str/bool/int/float/path] [--posix] [-o OUT]` | edits one key in place; `auto` keeps a bare value bare, otherwise quotes |
| `fmt FILE [-o OUT]` | writes the canonical form |
| `convert INPUT [OUTPUT]` | turns a plain INI into LabVIEW form; `true`/`false` and plain decimal numbers become bare tokens |

`--encoding` applies to every file. Errors, usage errors included, go to stderr with exit
status 1; an interrupt exits with 130.

## Upgrading from 0.3

- `escape` no longer writes `"` as `\22`, DEL as `\7F` or tab as `\09`: LabVIEW writes them
  as they are and reads `\22` back as text. `unescape` decodes only `\00` to `\1F` in upper
  case, and bare values are now unescaped too.
- A repeated key reads as its first value, not its last, and an edit changes that first line.
- Values are trimmed of spaces and tabs only.
- `to_bool` also reads `yes`, `no`, `on`, `off`, `t`, `f` and `y`. `to_int` refuses
  `1_000` and non-ASCII digits. `to_float` reads `2,5` and refuses `1_000`, `-NaN`,
  non-ASCII digits and blanks other than spaces and tabs.
- `get_path` resolves empty, `.` and `..` parts of a drive path, and refuses a UNC path
  stored with backslashes.
- The canonical form writes `key = value` and no final newline, as LabVIEW does; new keys
  in an edited file are written as `key = value`.
- Every function raises `TypeError` for an argument of the wrong type, and messages are cut
  to 40 characters of the offending text.
