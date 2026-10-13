# lvconfig 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.1)
- [x] Baseline gates run on 0.3.1
- [x] Real LabVIEW 2026 captures (item 7)
- [ ] API review and 1.0.0 API changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15)
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Baseline on 0.3.1 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest --doctest-modules src` | no doctests at all |

## Ground truth (item 7)

`tests/fixtures/labview2026/` holds what LabVIEW 2026 Community 26.3.1f1 wrote and read on
this PC on 2026-10-13. Shipped VIs that call the Configuration File VIs were run headless
through LabVIEW's ActiveX server with inputs chosen by the author; `manifest.json` records
which VI produced each file, its size and SHA-256.

Defects in 0.3.1 found against these captures:

- `escape` wrote `"` as `\22` and DEL as `\7F`; LabVIEW reads both back literally, so a value
  holding a double quote came back from LabVIEW as `\22`. LabVIEW's writer escapes only the
  codes below 0x20 other than tab, and doubles the backslash.
- `unescape` decoded `\XX` for every byte and for lower-case hex digits. LabVIEW decodes only
  `\00` to `\1F` in upper case.
- Unquoted values were not unescaped; LabVIEW decodes `\09` in a bare value too.
- A repeated key took its last value; LabVIEW reads the first.
- `to_bool` refused `yes`, `no`, `on`, `off`, `t`, `f` and `y`, which LabVIEW reads.
- `to_int("1_000")` returned 1000 and `to_float("1_000")` 1000.0; LabVIEW reads 1. Python's
  `int` and `float` also took Unicode digits and `to_float` refused `2,5`, which LabVIEW writes
  itself on a system whose decimal separator is a comma.
- Values were trimmed with `str.strip`, which also removes `\x1f`, `\x0b`, `\xa0` and other
  characters LabVIEW keeps; LabVIEW trims only spaces and tabs.
