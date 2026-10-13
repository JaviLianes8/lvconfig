# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1]

- The NI configuration file excerpts are no longer tracked or shipped in the sdist. The
  always-on tests use hand-written fixtures with the same syntax features;
  `scripts/capture_ni.py` cuts the NI excerpts from a local LabVIEW install (checked against
  the tracked manifest) and their tests skip when they are absent.

## [0.3.0]

- Byte-identical round-trip: `parse` records the source layout and `dump` writes every
  untouched line back verbatim, so `dump(parse(text)) == text`. Blank lines, `;` and `#`
  comments, `key = value` spacing, line endings, a missing final newline, repeated
  sections and a UTF-8 byte order mark all survive. An edited key is rewritten in place
  with its original spacing, a removed key takes its comment lines along, and new keys
  go after the section's last line in the source.
- `set` and `dump` raise `LvConfigError` instead of writing text that reads back as
  something else: keys with `=`, line breaks, edge whitespace or a leading `;`/`#`,
  section names with line breaks, quote-wrapped bare values, comments that are not
  comments, and header comments for a missing section.
- `to_labview_path` and `Config.set_path` gain `windows=True`. Pass `windows=False`
  for POSIX paths, which were previously passed through on any leading `/`.
- `dump(config, normalize=True)` writes the canonical form, which is what `dump`
  produced for parsed configs in 0.2.0. `Config.layout` holds the recorded layout and
  takes no part in equality.
- `load` keeps the file's line endings and `save` writes them back. `save` now defaults
  to `line_ending=None`, which still means `CRLF` for a config built in code.
- `#` comment lines and keys before the first section header (section `""`) are
  accepted. Both appear in files LabVIEW ships, which 0.2.0 could not parse.
- `Config.set` keeps the comment lines attached to the key it replaces.
- Special floats are written as `Inf`, `-Inf` and `NaN`.
- Fixed: `to_labview_path("C:x")` returned `/C/x`, which reads back as the different
  path `C:\x`. Drive-relative paths, rooted paths without a drive, UNC paths without a
  share and device paths now raise the new `LvPathError` on both encode and decode, as
  does reading a POSIX absolute value as a Windows path, or encoding `/dir` as one.
- CLI: `set` edits one key in place, `fmt` writes the canonical form, `--posix` handles
  POSIX paths, usage errors exit with status 1, `json --section` with an unknown section
  is an error, and output is written as UTF-8. `convert` only treats plain decimal
  numbers as numbers, so `007`, `1_000`, `1e5` and `nan` stay text.
- Golden fixtures copied from files installed with LabVIEW 2026, a contract test over
  them, and an end-to-end test that installs the package and runs the `lvconfig` script.

## [0.2.0]

- `load` and `save` read and write LabVIEW configuration files directly, defaulting to
  the `CRLF` line endings LabVIEW writes on Windows.
- Comment preservation: `parse` keeps whole-line `;` comments and attaches them to the
  section or key that follows them, and `dump` writes them back, so a parsed file keeps
  its annotations through a round-trip. `Entry.comments`, `Config.header_comments` and
  `Config.trailing_comments` expose them.
- `Config` gains `items`, `to_dict`, `remove` and `remove_section`.
- A command-line interface (`lvconfig`): `json` dumps a file as decoded JSON, `get`
  prints one typed value, and `convert` turns a plain `.ini` into LabVIEW-escaped form.

## [0.1.0]

- `parse` and `dump` for LabVIEW configuration text, preserving section and key order.
- `Config` container with typed getters and setters (`get_str`, `get_bool`, `get_int`,
  `get_float`, `get_path`, `set`, `set_path`).
- LabVIEW-correct `escape`/`unescape` for `\XX` hex codes and doubled backslashes.
- `to_labview_path`/`from_labview_path` for the platform-neutral stored path form.
- `to_bool`/`to_int`/`to_float` value coercion, including `TRUE`/`FALSE`/`0`/`1`.
- First release.
