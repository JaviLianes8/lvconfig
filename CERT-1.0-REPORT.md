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
| `pytest` | 261 collected: 238 passed, 23 skipped (the NI excerpts are local only) |
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

## Author mutation round (item 18)

Each mutation was applied alone to a clean clone on the laptop, the full suite run with `-x`
(all but `tests/test_cli_e2e.py`, whose console-script tests rebuild a virtual environment;
CLI mutations are caught in process), and the file restored. Bytecode was never written,
`__pycache__` was cleared before each run, and the suite was green before and after the round.
48 mutations: 45 killed at once, 3 survived and were killed by new contracts on re-application.

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | tab escaped as \09 | `_escape.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| M02 | space escaped too | `_escape.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| M03 | lower-case hex written | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._dump]` |
| M04 | backslash not doubled | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| M05 | lower-case hex decoded | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| M06 | \7X codes decoded | `_escape.py` | killed | `test_escape.py::test_unescape_keeps_a_backslash_that_is_not_a_labview_code[\\7F]` |
| M07 | raw ignored | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| M08 | y not true | `_coerce.py` | killed | `test_labview_captures.py::test_a_boolean_reads_as_labview_reads_it[y-True]` |
| M09 | n read as false | `_coerce.py` | killed | `test_labview_captures.py::test_a_boolean_reads_as_labview_reads_it[n-None]` |
| M10 | underscores in integers | `_coerce.py` | killed | `test_labview_captures.py::test_an_integer_reads_as_labview_reads_it_or_is_refused[1_000]` |
| M11 | comma separator not converted | `_coerce.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._coerce]` |
| M12 | -Inf read as +inf | `_coerce.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._coerce]` |
| M13 | -NaN accepted | `_coerce.py` | survived, then killed | new `test_hostile_more.py::test_only_an_unsigned_nan_reads_as_nan[-NaN]` |
| M14 | to_int trims every blank | `_coerce.py` | survived, then killed | new `test_hostile_more.py::test_numbers_are_trimmed_of_spaces_and_tabs_only` |
| M15 | last repeated key wins | `_parse.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._parse]` |
| M16 | bare values not unescaped | `_parse.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| M17 | values trimmed of every blank | `_parse.py` | killed | `test_labview_captures.py::test_a_value_reads_as_labview_reads_it[597]` |
| M18 | single quotes kept | `_parse.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| M19 | key not right-trimmed | `_parse.py` | killed | `test_cli_edit.py::test_set_with_types_and_output` |
| M20 | Python spelling of infinity | `_entry.py` | killed | `test_lossless.py::test_special_floats_use_labview_spelling[inf-Inf]` |
| M21 | bool written as int | `_entry.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| M22 | float subclass repr trusted | `_entry.py` | killed | `test_hostile.py::test_subclasses_are_written_as_the_value_they_hold` |
| M23 | dot parts kept | `_path.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._path]` |
| M24 | .. refused everywhere | `_path.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._path]` |
| M25 | climb above root ignored | `_path.py` | killed | `test_promises.py::test_path_promise` |
| M26 | native UNC accepted | `_path.py` | killed | `test_labview_captures.py::test_a_path_reads_as_labview_reads_it_or_is_refused["\\\\\\\\server\\\\share"]` |
| M27 | drive root stored with a slash | `_path.py` | killed | `test_path.py::test_bare_drive_stores_without_a_trailing_slash` |
| M28 | semicolon allowed in bare values | `_validate.py` | killed | `test_hostile.py::test_untouched_lines_are_never_refused_even_when_labview_reads_them_oddly` |
| M29 | header-like key line allowed | `_validate.py` | killed | `test_validation.py::test_a_bracket_key_is_refused_only_when_it_would_read_as_a_header` |
| M30 | untouched bare lines re-checked | `_validate.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| M31 | key=value without spaces | `_dump.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| M32 | final newline written | `_dump.py` | killed | `test_cli_edit.py::test_fmt_prints_the_canonical_form` |
| M33 | headerless keys not first | `_dump.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| M34 | leading U+FEFF not protected | `_dump.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| M35 | removed key keeps its comments | `_lossless.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| M36 | new keys without spaces | `_lossless.py` | killed | `test_io.py::test_an_edit_after_load_keeps_crlf_on_the_new_line` |
| M37 | built configs saved with LF | `_io.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._io]` |
| M38 | any line ending accepted | `_io.py` | killed | `test_hostile.py::test_error_messages_stay_short_for_huge_input[<lambda>9]` |
| M39 | interrupt exits 1 | `_cli.py` | killed | `test_hostile.py::test_the_cli_exits_130_on_an_interrupt` |
| M40 | unknown encoding traceback | `_cli.py` | killed | `test_hostile.py::test_the_cli_reports_a_bad_encoding_without_a_traceback` |
| M41 | messages unbounded | `_cli.py` | killed | `test_hostile.py::test_the_cli_does_not_echo_huge_arguments` |
| M42 | message cut far later | `_check.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._check]` |
| M43 | str subclass passed through | `_check.py` | survived, then killed | new `test_hostile_more.py::test_plain_str_comes_back_even_for_a_str_subclass` |
| M44 | get_path ignores windows | `_reading.py` | killed | `test_config.py::test_get_path_can_decode_for_posix` |
| M45 | get ignores its default | `_reading.py` | killed | `test_config.py::test_get_returns_the_default_when_missing` |
| M46 | set drops the key's comments | `_config.py` | killed | `test_lossless.py::test_setting_the_same_value_changes_nothing` |
| M47 | empty unnamed section kept | `_config.py` | killed | `test_validation.py::test_an_empty_unnamed_section_writes_nothing` |
| M48 | set_path ignores windows | `_config.py` | killed | `test_path_refusals.py::test_posix_encoding_keeps_the_path` |
