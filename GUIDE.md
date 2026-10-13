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
| `X = 1` then `x = 2` | `'1'` under `X` | names differing only in case are repeats, as in LabVIEW |
| `note = abc ; c  ` | `'abc; c  '` | a bare `;` starts a comment: the text before it is trimmed, the rest kept as written |
| `note = "a ; b"` | `'a ; b'` | inside quotes `;` is text |
| `[T] x=y` or `[S] ; note` | a header | a line starting with `[` and holding `]` is a header, named by the text between its first character and its last `]` (so `  [T]` names ` [T`), as LabVIEW reads it |

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

`get_bool`, `get_int`, `get_float` and `get_path` read the stored text, as LabVIEW's
typed Read Key VIs do: `\XX` codes are not decoded (`TRUE\09` is not a boolean), and the
first three stop at a bare `;` (`TRUE ; note` reads as `True`). LabVIEW's Read Key (I32)
clamps to 32 bits; `get_int` returns the full Python integer.

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
is written as it is. A bare value (a number, or an entry made with `quoted=False`) is
written bare only when LabVIEW reads it back unchanged: no leading blank, no trailing one
except after a `;`, no surrounding
quotes and no blank just before a `;`; `set` quotes every `str`.

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
| `a/./b/../c` or `rel\\..\\x` (relative) | `a\c` or `x`; a leading `..` is kept |
| `//server/share/a/../b` | `\\server\share\b` |

As LabVIEW's Read Key (Path) does, every `/` and every backslash of the stored text is a
separator, empty and `.` parts are dropped and `..` goes up one level. On Windows
`get_path` resolves the stored text itself, without decoding `\XX` codes, as LabVIEW does:
`/C/\09x` is `C:\09x`. With `windows=False` it returns the decoded value unchanged.

`to_labview_path` and `set_path` go the other way. Pass `windows=False` (or `--posix` on
the command line) for POSIX paths, which are already in stored form.

A path that has no faithful counterpart raises `LvPathError` instead of turning into a
path to another file: a drive-relative `C:file` or bare `C:`, a rooted path without a drive
(`\dir`, `/dir`), a UNC path without a share, a `\\?\` device path, a POSIX absolute value
such as `/usr/lib` read as Windows (LabVIEW reads it as `u:\sr\lib`), a malformed `/C:/x`,
a `..` above a drive root or share, a UNC path stored with backslashes, and (when storing)
a path holding a control character.

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

- an edited key is rewritten in place, keeping its `key = ` spacing and line ending; a
  `; note` after a bare value is part of that value, so setting the key replaces it too;
- a removed key or section disappears with its comment lines, and a removed key takes its
  repeated lines along, so no older value comes back;
- a new key goes after the last line of its section's first block (the block LabVIEW
  reads), a new section at the end of the file;
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
separates lines with `\n`; `save` writes LabVIEW's `\r\n` for a config built in code. For
the captured files without comments or repeated keys it is byte for byte what LabVIEW
wrote; values keep the text they were read from, and a value built in code is written in
lvconfig's own spelling (double quotes, a tab in a bare value as `\09`), which LabVIEW
reads as the same string. An empty unnamed section is written as a `[]` line.

A bare value with a `;` is written bare again only when LabVIEW reads it back unchanged
(no blank just before the first `;`); a value parsed from a file always is.

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
is rendered and encoded first, written to a temporary file in the same folder, and that
file then replaces the target; a refused config, an encoding error, a full disk or a locked
file leaves the old file as it was. Because the file is replaced, it is a new file: links
to the old one and its permissions are not carried over.

## Errors

| Error | Raised by | When |
| --- | --- | --- |
| `LvParseError` (an `LvConfigError`, with `.line`) | `parse`, `load` | a line that is not a section, key or comment |
| `LvConfigError` | `to_bool`, `to_int`, `to_float` and the getters | text that is not that type |
| `LvConfigError` | `set`, `dump`, `save` | a key with `=`, a line break or edge blanks, a key starting with `;` or `#`, a section name with a line break, a bare value LabVIEW would read differently, a comment that does not start with `;` or `#` or ends in blanks, header comments for a missing section, two section or key names that differ only in case, an integer longer than Python turns into text (4300 digits by default) |
| `LvPathError` (an `LvConfigError` and a `ValueError`) | the path functions, `set_path`, `get_path` | a path with no faithful counterpart |
| `KeyError` | `get_str` and the typed getters | a missing section or key (`get` returns a default instead) |
| `TypeError` | every function | an argument of the wrong type, a path that is not a `str` or text `os.PathLike`, or a `Config` whose fields `dump` finds holding the wrong objects |
| `ValueError` | `save` | a `line_ending` other than `None`, CRLF, LF or CR |
| `OSError`, `UnicodeDecodeError`, `LookupError` | `load` | the file cannot be read, is not in `encoding`, or `encoding` is unknown |
| `OSError`, `UnicodeEncodeError`, `LookupError` | `save` | the file cannot be written, a value is not in `encoding`, or `encoding` is unknown; the text is encoded before the file is opened, so the file is left as it was |

The library's messages quote at most 40 characters of the offending text, so a huge value
never floods a log; the command line cuts any message, its own or Python's, at 300
characters. `Config`'s fields are plain data: the getters assume they hold what their types say,
and only `dump` checks them (an empty tuple in `header_comments` is written as no comments,
and a parse records no entry for it). `Config.layout` is an opaque record of the source text; keep
the one `parse` made, or set it to `None`.

## Where lvconfig and LabVIEW differ

Wherever both find a value it is the same value, checked against three LabVIEW capture
runs. These are the places where they do not both find one; each is pinned by a test:

- Lookups. LabVIEW matches section and key names without regard to the case of A-Z and
  the Latin-1 capitals. lvconfig reads a file the same way (a later `x` after `X` is a
  repeat, a later `[s]` is a block of `[S]`, the first spelling stands), but its methods
  and the command line match names exactly, so `get("S", "x")` finds nothing when the
  file spells it `X`. `dump` refuses two names that differ only in case.
- Hidden keys. LabVIEW sees only the first block of a repeated section and nothing before
  the first header or under `[]`. lvconfig merges every block of a section and keeps
  headerless keys in the section `""`, so it returns values LabVIEW never reads. Edits
  follow LabVIEW: new keys, and new values of keys found only in a later block, are
  written into the first block. `dump(config, normalize=True)` writes the merged
  sections, so keys LabVIEW could not see become visible to it: it is a rewrite, not a
  reformat.
- Lines. LabVIEW reads a line with no `=` as a key with an empty value, and a `;` or `#`
  line holding `=` as a key named `;k` or `#k`. `parse` raises `LvParseError` for a line
  with no `=` and reads `;` and `#` lines as comments.
- Text. LabVIEW reads files in the system code page and does not skip a UTF-8 byte order
  mark; `load` reads UTF-8 by default and skips one. Pass `encoding="cp1252"` (or your
  system's code page) to read and write what LabVIEW does.
- Numbers. LabVIEW reads the leading part of `12abc`, `1_000` or `0x10`, and clamps
  integers to 32 bits; lvconfig refuses partial numbers and returns every digit, so
  `get_int` of `4294967295` is 4294967295 where LabVIEW's Read Key (I32) gives 2147483647.
- Paths. LabVIEW reads `C:` as `C:\`, `:x` as `C:\x`, and a `..` above a drive root or
  share as some other path; lvconfig refuses them.

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
| `convert INPUT [OUTPUT]` | turns a plain INI into LabVIEW form; `true`/`false` and plain decimal numbers become bare tokens; keys of a `[DEFAULT]` section are copied into every section, as `configparser` reads them |

`--encoding` applies to every file. Errors, usage errors included, go to stderr with exit
status 1; an interrupt exits with 130.

## Upgrading from 0.3

- `escape` no longer writes `"` as `\22`, DEL as `\7F` or tab as `\09`: LabVIEW writes them
  as they are and reads `\22` back as text. `unescape` decodes only `\00` to `\1F` in upper
  case, and bare values are now unescaped too.
- A repeated key reads as its first value, not its last, and an edit changes that first line.
  Names that differ only in case are repeats; new keys go into a section's first block.
- A bare `;` starts a comment as in LabVIEW, and the typed getters stop at it.
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
