# lvconfig round 2: ranked improvements

Ranked by impact on the core promise: read a LabVIEW configuration file, change what
you mean to change, and write back a file LabVIEW reads exactly as before.

Each item was checked against configuration files shipped with LabVIEW 2026.

## Implemented in 0.3.0

1. **Byte-identical round-trip.** `dump(parse(text))` rebuilt the file in a canonical
   form: blank lines, `key = value` spacing, line endings, a missing final newline and
   repeated sections were all rewritten. The README already promised a lossless
   round-trip. `parse` now records the source layout, and `dump` writes every untouched
   line back verbatim. Only edited keys are rewritten, keeping their original
   `key = ` spacing.
2. **Drive-relative paths changed meaning.** `to_labview_path("C:x")` returned `/C/x`,
   which reads back as `C:\x`. Drive-relative (`C:x`, `C:`), rooted paths without a
   drive (`\dir`), incomplete UNC paths and device paths are now refused with
   `LvPathError`, on the same rules as the sibling `lvpath` 0.3.0. Reading a POSIX
   absolute path as Windows is refused too, instead of turning `/usr/lib` into
   `\usr\lib`.
3. **Shipped files failed to parse.** `#` comment lines (used by LabVIEW's own web
   service and LINX files) raised `LvParseError`. Keys before the first section (used
   by `mxLvProvider.ini`) raised too. Both are now accepted. Keys before any section
   live in the section named `""`.
4. **Line endings and BOM survive `load`/`save`.** `load` read in universal-newline
   mode and dropped `CRLF`. It now keeps the exact endings. `save` keeps them unless a
   `line_ending` is passed. A UTF-8 byte order mark is kept too.
5. **Golden fixtures from a real install.** Verbatim excerpts of LabVIEW 2026 files
   are committed under `tests/fixtures/labview2026/` with their source paths. Contract
   tests prove a byte-identical round-trip, typed reads and path conversion against
   them. When LabVIEW is installed, an extra test round-trips every shipped `.ini`.
6. **`dump(config, normalize=True)`.** Writes the canonical form on demand, which is
   the 0.2.0 behaviour.
7. **CLI `set` and `fmt` commands.** `set` edits one key in place and leaves every
   other byte alone. `fmt` writes the canonical form. Usage errors also exit 1 on
   stderr. `json --section` with an unknown section is an error instead of `{}`.
   Output is written as UTF-8.
8. **Special floats in LabVIEW spelling.** `set(..., float("inf"))` writes `Inf`,
   `-Inf` and `NaN` as LabVIEW does, not Python's `inf`.
9. **Real end-to-end test.** Installs the package into a throwaway virtual
   environment and drives the installed `lvconfig` script as a subprocess.

## Considered, not done

- **Typed getters with a fallback** (`get_int(..., default=3)`). Useful, but it needs
  overloads for a clean typed signature. `get` already returns a default.
- **Encoding detection.** LabVIEW writes files in the system code page. A wrong
  `encoding` fails loudly instead of corrupting data, and `--encoding` exists.
- **`//` comments.** One shipped template has a `// key=value` line. LabVIEW does not
  document `//` as a comment, so it stays a key named `// key` and still round-trips.
- **Section reordering on dump.** The source order wins. New sections are appended.
