# lvconfig 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.1)
- [x] Baseline gates run on 0.3.1
- [x] Real LabVIEW 2026 captures (item 7), three runs
- [x] API review and 1.0.0 API changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15)
- [ ] PR and trace guard CLEAN (item 17); merge and publish left to the maintainer

## Scorecard

SCORECARD

## Baseline on 0.3.1 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 261 collected: 238 passed, 23 skipped (the NI excerpts are local only) |
| `pytest --doctest-modules src` | no doctests at all |

## Ground truth (item 7)

`tests/fixtures/labview2026/` holds what LabVIEW 2026 Community 26.3.1f1 wrote and read on
this PC on 2026-10-13, in three capture runs. Shipped VIs that call the Configuration File
VIs (GPFW NI_ReadToken_String and _Bool, Read FW INI, writeUserModePref, and the Read and
Write Configuration (INI) File examples) were run headless through LabVIEW's ActiveX server;
`manifest.json` records which VI produced each file, its size and SHA-256. The first run used
the author's inputs (551 writes, 812 string reads, 26 paths, 26 integers, 39 booleans, 31
doubles, 8 rewrites, the lookup semantics file); the second and third used case lists written
by the two independent ground-truth reviewers (53 + 392 lookups, 41 booleans, 63 paths, 36
integers, 22 rewrites; 320 of the third run's lookups seeded). The tests compare lvconfig with
every capture: wherever both find a value it is the same value, and every place where they do
not both find one is listed in GUIDE.md and pinned by a test.

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
- Names were matched exactly; LabVIEW treats names differing only in the case of A-Z or the
  Latin-1 capitals as one, so a later `x` after `X` gave lvconfig a different value.
- A bare `;` was text to lvconfig; LabVIEW reads it as a comment and returns a rejoined value,
  and its typed reads stop at it.
- Any line starting with `[` and holding `]` is a header to LabVIEW (`[S] ; note`, `[T] x=y`);
  lvconfig refused the first and read the second as a key.
- LabVIEW's typed and path reads work on the stored text without decoding `\XX` codes, and it
  resolves `.`, `..`, empty parts and backslashes in every path form; lvconfig decoded and kept
  them.
- New keys and edits of a repeated section went into its last block, which LabVIEW never reads.

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
| M47 | empty unnamed section kept | `_config.py` | killed | `test_validation.py::test_an_empty_unnamed_section_writes_nothing` (since renamed `test_an_empty_unnamed_section_keeps_its_bracket_line`) |
| M48 | set_path ignores windows | `_config.py` | killed | `test_path_refusals.py::test_posix_encoding_keeps_the_path` |

## Packaging and end-to-end (items 8, 10, 14)

Run by lens d on the laptop, each time from a fresh clone (final run at ff12c58, re-checked
at 11cd75d):

- `python -m build` and `twine check --strict`: both artifacts pass. The wheel holds the 20
  package modules, `py.typed`, LICENSE and the entry point; the sdist adds the tests with the
  hand-written fixtures and the LabVIEW captures, `tests/fixtures/ni/MANIFEST.json` (no NI
  `.ini` file: a planted one was left out of both artifacts), `scripts/capture_ni.py`,
  `scripts/check.ps1`, `requirements-dev.txt`, `.gitattributes`, the docs and LICENSE.
- The wheel in fresh venvs, the suite run from the extracted sdist with `src` removed and
  `LVCONFIG_INSTALLED=1` so the CLI tests drive the installed console script: 3.10.22
  (2635 passed, 24 skipped), 3.11.17, 3.12.15, 3.13.16, 3.14.6 and 3.14.8t free-threaded
  (2636 passed, 23 skipped each). The skips are the local-only NI excerpts and the installed
  LabVIEW test. Replacing or deleting the installed `lvconfig.exe`, or changing the
  installed module, makes the CLI tests fail.
- PyPI 0.2.0 installed, then upgraded in place to the 1.0.0 wheel: 126 probes, 80 changed,
  every change listed in CHANGELOG 1.0.0 or the unpublished 0.3.0 and 0.3.1 sections.

## Independent QA lenses (item 19)

Every lens was a fresh reviewer that read the certification rules first, worked in its own
clone, ran things rather than reading, and reported back privately. A lens that failed was
re-run by a new reviewer with the same lens after the fixes.

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a. API and docs | 1 | 8917da2 | FAIL | `LvParseError` not picklable, `Config.get` typing, stored paths the reader refuses, CHANGELOG gaps, int paths taken as file descriptors, exceptions without examples, CLI messages unbounded. Fixed in d9dcd87 |
| a | 2 | d4ac642 | FAIL | UNC `..` and control characters stored, docs contradicting the code on bare `;`, device-path message, `convert` errors naming `<string>`. Fixed in 3701820 |
| a | 3 | ff12c58 | FAIL | docstring and guide wording only (new-key placement, `get_path` on POSIX, `get` default type). Fixed in da668e1 |
| a | 4 | 11cd75d | PASS | all earlier findings verified fixed; two wording leftovers fixed in a8a3007 |
| b. Correctness and ground truth | 1 | 8917da2 | FAIL | single quotes without ground truth, case-variant names, edits landing in hidden blocks, bare `;` edges, relative and UNC paths. Second LabVIEW capture run; fixed in d4ac642 |
| b | 2 | d4ac642 | FAIL | accented case, header lines, indented headers, typed reads decoding codes, later-block edits. Third LabVIEW capture run; fixed in a599af2 |
| b | 3 | 1998a1f | FAIL | Windows-1252 case folding, blank-looking lines as empty keys, undocumented differences. Fixed in a8a3007 |
| b | 4 | a8a3007 | FAIL | the blank-line fix added a `[]` line to some files; a moved key's comment left behind. Fixed in cd8d950 and 5f29389 |
| c. Adversarial and robustness | 1 | 8917da2 | FAIL | failed saves emptied the file, quadratic repeated headers, undocumented `ValueError`, lying subclasses. Fixed in d9dcd87 |
| c | 2 | 15440fe | FAIL | a failed write after opening emptied the file, bare values reading as quoted or as headers, subclasses in Config fields. Fixed in d8a0bf0 (temporary file and `os.replace`) |
| c | 3 | 11cd75d | FAIL | a moved edit dropped the key's comments. Fixed in 5f29389 |
| c | 4 | 5f29389 | FAIL | the `[]` regression (fixed in cd8d950); blank lines above a removed header dropped (fixed in 04ba94c) |
| d. Packaging and real e2e | 1 | 8917da2 | PASS | low findings: CONTRIBUTING files missing from the sdist, release script. Fixed in 6744d79 |
| d | 2 | ff12c58 | FAIL | `.gitattributes` missing from the sdist, upgrade notes from 0.3 only, gate script not stopping. Fixed in 1998a1f |
| d | 3 | 11cd75d | PASS | all fixed |
| e. Contract strength | 1 | 8917da2 | FAIL | 145 mutations, 29 survivors closed by `test_mutation_contracts.py` and `test_mutation_cli_contracts.py`, 4 equivalent |
| e | 2 | 15440fe | FAIL | round 1 survivors killed but one; 68 new, 17 survivors closed by `test_mutation_contracts_two.py`, 2 equivalent |
| e | 3 | 11cd75d | PASS with its contracts | round 2 survivors killed (W7 proven equivalent); 74 new, 8 survivors closed by `test_mutation_contracts_three.py`, 3 equivalent |
FINAL_ROUNDS
## Blind mutation rounds by lens e (items 18 and 19e)

Each round was designed from the source and GUIDE.md alone, run one mutation at a time on
the laptop with no bytecode written, `__pycache__` cleared, a per-mutant timeout, and the
baseline green before and after. "Survived, then killed" rows were closed by the contract
files named above; each new contract was shown to fail on its mutant and pass on the
original.

### Round 1 (8917da2)

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| E1 | escape: space (0x20) also hex-escaped (< becomes <=) | `_escape.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| E2 | escape: tab no longer exempt from hex escaping | `_escape.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| E3 | escape: lower-case hex digits | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._dump]` |
| E4 | unescape: first hex digit range widened to 0-2 | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| E5 | unescape: lower-case hex accepted as code | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| E6 | unescape: off-by-one, code at end of string not decoded | `_escape.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| E7 | escape: backslash not doubled | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| E8 | unescape: doubled backslash advances one char only | `_escape.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._escape]` |
| E9 | escape: raw flag type validation dropped | `_escape.py` | killed | `test_escape.py::test_raw_must_be_a_bool` |
| C1 | to_bool: 'y' dropped from true spellings | `_coerce.py` | killed | `test_labview_captures.py::test_a_boolean_reads_as_labview_reads_it[y-True]` |
| C2 | to_bool: 'f' dropped from false spellings | `_coerce.py` | killed | `test_labview_captures.py::test_a_boolean_reads_as_labview_reads_it[f-False]` |
| C3 | to_bool: strips every whitespace, not only space/tab | `_coerce.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| C4 | to_int: leading '+' sign rejected | `_coerce.py` | killed | `test_labview_captures.py::test_an_integer_reads_as_labview_reads_it_or_is_refused[+5]` |
| C5 | to_int: prefix match instead of full match | `_coerce.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| C6 | to_int: wrong error type (ValueError) for over-long integer | `_coerce.py` | killed | `test_fuzz.py::test_long_numbers_and_paths_stay_fast` |
| C7 | to_float: comma decimal separator after digits dropped | `_coerce.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._coerce]` |
| C8 | to_float: upper-case exponent E rejected | `_coerce.py` | killed | `test_labview_captures.py::test_a_double_reads_as_labview_reads_it_or_is_refused[1E3-1000.0]` |
| C9 | to_float: Inf no longer case-insensitive | `_coerce.py` | killed | `test_coerce.py::test_labview_infinity_reads_as_inf` |
| C10 | to_float: sign of infinity dropped | `_coerce.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._coerce]` |
| C11 | to_float: NaN only lower-case | `_coerce.py` | killed | `test_coerce.py::test_labview_nan_reads_as_nan` |
| C12 | to_float: trailing-dot number '1.' rejected | `_coerce.py` | killed | `test_labview_captures.py::test_a_double_reads_as_labview_reads_it_or_is_refused[5.-5.0]` |
| C13 | to_float: '.5' leading-dot form rejected | `_coerce.py` | killed | `test_labview_captures.py::test_a_double_reads_as_labview_reads_it_or_is_refused[.5-0.5]` |
| K1 | short: message bound raised from 40 to 400 | `_check.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._check]` |
| K2 | short: boundary off by one (<= becomes <) | `_check.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| K3 | need_bool: accepts int | `_check.py` | killed | `test_escape.py::test_raw_must_be_a_bool` |
| K4 | need_str: returns str subclass instance as is | `_check.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| K5 | type_name: no truncation of long type names | `_check.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| N1 | make_entry: booleans written True/False | `_entry.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| N2 | make_entry: NaN spelled the Python way | `_entry.py` | killed | `test_lossless.py::test_special_floats_use_labview_spelling[nan-NaN]` |
| N3 | make_entry: infinity sign swapped | `_entry.py` | killed | `test_lossless.py::test_special_floats_use_labview_spelling[inf-Inf]` |
| N4 | make_entry: str(value) for ints (IntEnum override leaks) | `_entry.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| N5 | make_entry: strings stored unquoted | `_entry.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| N6 | Entry: comments may be a list | `_entry.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| N7 | make_entry: bool checked after int (bool becomes 1/0) | `_entry.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| P1 | parse: single quotes not stripped | `_parse.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| P2 | parse: lone quote char treated as empty quoted string (>=1) | `_parse.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| P3 | parse: bare values not unescaped | `_parse.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| P4 | parse: repeated key, last one wins | `_parse.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._parse]` |
| P5 | parse: error line numbers zero-based | `_parse.py` | killed | `test_hostile.py::test_a_parse_error_names_its_line` |
| P6 | parse: tabs not trimmed | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| P7 | parse: section names trimmed | `_parse.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| P8 | parse: BOM not stripped | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| P9 | parse: split at last '=' instead of first | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| P10 | parse: repeated-section header comments not merged | `_parse.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| P11 | parse: final_eol forced to layout eol | `_parse.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| P12 | parse: default eol for no-newline input is CRLF | `_parse.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| P13 | parse: quoted value not unescaped | `_parse.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._parse]` |
| L1 | split_lines: CRLF split as LF + extra line | `_layout.py` | equivalent | equivalent: at a CR the LF alternative cannot match, so CRLF is still tried first |
| L2 | split_lines: empty final line appended (< becomes <=) | `_layout.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| L3 | is_comment: '#' not a comment | `_layout.py` | killed | `test_cli_edit.py::test_set_auto_keeps_a_quoted_value_quoted` |
| L4 | split_lines: lone CR not a line terminator | `_layout.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| H1 | path: lower-case drive letters not recognised | `_path.py` | killed | `test_handwritten_fixtures.py::test_stored_paths_encode_back_to_the_stored_text` |
| H2 | path: drive-relative C:file accepted (only bare C: refused) | `_path.py` | killed | `test_cli_edit.py::test_set_refuses_a_drive_relative_path` |
| H3 | path: UNC without share accepted | `_path.py` | killed | `test_labview_captures.py::test_a_path_reads_as_labview_reads_it_or_is_refused["//server"]` |
| H4 | path: \\.\ device paths not refused | `_path.py` | killed | `test_path_refusals.py::test_device_path_is_refused[\\\\.\\COM1]` |
| H5 | path: '..' above drive root silently ignored | `_path.py` | killed | `test_promises.py::test_path_promise` |
| H6 | path: '.' parts kept | `_path.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._path]` |
| H7 | to_labview_path: bare drive root becomes /C/ | `_path.py` | killed | `test_path.py::test_bare_drive_stores_without_a_trailing_slash` |
| H8 | from_labview_path: POSIX absolute path not refused | `_path.py` | equivalent | equivalent: every value it lets through is refused later as rooted without a drive |
| H9 | from_labview_path: malformed-drive check dropped | `_path.py` | equivalent | equivalent: every value it lets through is refused later as rooted without a drive |
| H10 | from_labview_path: empty-path shortcut dropped | `_path.py` | equivalent | equivalent: an empty path falls through every branch unchanged |
| H11 | to_labview_path: UNC loses one leading slash | `_path.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._path]` |
| H12 | from_labview_path: native-form UNC not refused | `_path.py` | killed | `test_labview_captures.py::test_a_path_reads_as_labview_reads_it_or_is_refused["\\\\\\\\server\\\\share"]` |
| H13 | to_labview_path: windows=False ignored | `_path.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._path]` |
| R1 | get: default ignored | `_reading.py` | killed | `test_config.py::test_get_returns_the_default_when_missing` |
| R2 | get_path: windows flag inverted | `_reading.py` | killed | `test_cli.py::test_get_decodes_a_path` |
| R3 | missing key raises LookupError instead of KeyError | `_reading.py` | killed | `test_config.py::test_get_str_raises_key_error_when_missing` |
| R4 | get_float: plain float() instead of to_float | `_reading.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[README.md]` |
| R5 | get_bool: truthiness of text | `_reading.py` | killed | `test_handwritten_fixtures.py::test_booleans_in_every_spelling_labview_writes` |
| V1 | check_section: CR not refused | `_validate.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| V2 | check_key: '=' in key accepted | `_validate.py` | killed | `test_hostile.py::test_error_messages_stay_short_for_huge_input[<lambda>6]` |
| V3 | check_key: tab edge whitespace not refused | `_validate.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| V4 | check_key: key starting with '#' accepted | `_validate.py` | killed | `test_validation.py::test_set_refuses_a_key_that_would_read_back_differently[#k]` |
| V5 | check_key: header-lookalike check inverted on quoting | `_validate.py` | killed | `test_validation.py::test_a_bracket_key_is_refused_only_when_it_would_read_as_a_header` |
| V6 | is_bare_safe: ';' accepted | `_validate.py` | killed | `test_hostile.py::test_untouched_lines_are_never_refused_even_when_labview_reads_them_oddly` |
| V7 | is_bare_safe: single-quote pair accepted | `_validate.py` | killed | `test_validation.py::test_dump_refuses_a_bare_value_that_would_change['x']` |
| V8 | check_comments: '/' accepted as comment start | `_validate.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| V9 | check_config: header comments for missing section accepted | `_validate.py` | killed | `test_validation.py::test_dump_refuses_header_comments_for_a_missing_section` |
| V10 | check_config: kept keys re-checked | `_validate.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| V11 | check_config: trailing comments unchecked | `_validate.py` | killed | `test_hostile.py::test_error_messages_stay_short_for_huge_input[<lambda>8]` |
| V12 | check_comments: line break in comment accepted | `_validate.py` | killed | `test_validation.py::test_dump_refuses_a_comment_that_is_not_a_comment[;` |
| V13 | is_bare_safe: edge blanks accepted | `_validate.py` | killed | `test_validation.py::test_dump_refuses_a_bare_value_that_would_change[` |
| G1 | set_path: stored unquoted | `_config.py` | killed | `test_cli_edit.py::test_set_with_types_and_output` |
| G2 | remove: unnamed section dropped even with header comments | `_config.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| G3 | remove_section: header comments left behind | `_config.py` | killed | `test_config.py::test_remove_section_drops_its_keys_and_comments` |
| G4 | set: replacing a key drops its comments | `_config.py` | killed | `test_lossless.py::test_setting_the_same_value_changes_nothing` |
| G5 | set: key validation dropped | `_config.py` | killed | `test_hostile.py::test_error_messages_stay_short_for_huge_input[<lambda>6]` |
| G6 | keys: sorted instead of insertion order | `_config.py` | killed | `test_parse.py::test_parse_keeps_section_and_key_order` |
| G7 | remove: empty unnamed section kept | `_config.py` | killed | `test_validation.py::test_an_empty_unnamed_section_writes_nothing` |
| G8 | set: section name validation dropped | `_config.py` | killed | `test_validation.py::test_set_refuses_a_section_name_with_a_line_break` |
| D1 | line: no spaces around '=' | `_dump.py` | killed | `test_cli.py::test_convert_escapes_a_plain_ini` |
| D2 | canonical: no blank line between sections | `_dump.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| D3 | canonical: final newline added | `_dump.py` | killed | `test_cli_edit.py::test_fmt_prints_the_canonical_form` |
| D4 | canonical: headerless keys not moved first | `_dump.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| D5 | render: bare value not escaped | `_dump.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| D6 | section_lines: no [] line for unnamed section comments | `_dump.py` | killed | `test_validation.py::test_header_comments_of_the_unnamed_section_keep_a_bracket_line` |
| D7 | dump: normalize flag ignored | `_dump.py` | killed | `test_cli_edit.py::test_fmt_prints_the_canonical_form` |
| D8 | protect_bom: leading U+FEFF not protected | `_dump.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| D9 | dump: validation skipped in canonical path | `_dump.py` | killed | `test_hostile.py::test_error_messages_stay_short_for_huge_input[<lambda>8]` |
| W1 | shadowed repeated-key lines dropped | `_lossless.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| W2 | edited key loses original spacing | `_lossless.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| W3 | edited key loses trailing whitespace | `_lossless.py` | killed | `test_lossless.py::test_editing_a_value_rewrites_only_its_line` |
| W4 | edited key uses layout eol, not its own | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| W5 | new section: blank line even at start of output | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| W6 | removed key: blank lines around it dropped | `_lossless.py` | killed | `test_lossless.py::test_removing_a_key_drops_its_comment_lines` |
| W7 | kept_keys: shadowed items counted | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| W8 | cleared trailing comments ignored | `_lossless.py` | killed | `test_lossless.py::test_edited_header_and_trailing_comments_are_written` |
| W9 | _join: last line gets its own eol instead of final_eol | `_lossless.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| W10 | new unnamed section emitted twice | `_lossless.py` | killed | `test_lossless.py::test_a_new_headerless_key_goes_at_the_top` |
| W11 | edited comments of repeated section not written | `_lossless.py` | killed | `test_lossless.py::test_edited_header_and_trailing_comments_are_written` |
| W12 | BOM dropped on lossless write | `_lossless.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| W13 | new keys never appended to existing sections | `_lossless.py` | killed | `test_io.py::test_an_edit_after_load_keeps_crlf_on_the_new_line` |
| W14 | removed section's header still written | `_lossless.py` | killed | `test_lossless.py::test_removing_a_section_drops_every_block_of_it` |
| W15 | new key comments not written | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| I1 | load: newline translation on | `_io.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| I2 | save: built config defaults to LF | `_io.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._io]` |
| I3 | save: CR line ending refused | `_io.py` | survived, then killed | new contract in `test_mutation_contracts.py` |
| I4 | save: wrong error type for bad line_ending | `_io.py` | killed | `test_hostile.py::test_error_messages_stay_short_for_huge_input[<lambda>9]` |
| I5 | save: newline translation on when writing | `_io.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| I6 | save: file opened before dump (refused config truncates file) | `_io.py` | killed | `test_hostile.py::test_a_refused_config_leaves_the_file_untouched` |
| X1 | usage error exits 2 instead of 1 | `_cli.py` | killed | `test_cli_edit.py::test_usage_errors_exit_one_on_stderr` |
| X2 | interrupt exits 1 instead of 130 | `_cli.py` | killed | `test_hostile.py::test_the_cli_exits_130_on_an_interrupt` |
| X3 | error message bound 300 -> 3000 | `_cli.py` | killed | `test_hostile.py::test_the_cli_does_not_echo_huge_arguments` |
| X4 | LookupError not handled (traceback) | `_cli.py` | killed | `test_hostile.py::test_the_cli_reports_a_bad_encoding_without_a_traceback` |
| X5 | broken pipe exits 0 | `_cli.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| X6 | default encoding cp1252 | `_cli.py` | killed | `test_hostile.py::test_the_cli_reports_undecodable_files` |
| X7 | error message printed to stdout | `_cli.py` | killed | `test_cli.py::test_get_missing_key_reports_an_error` |
| X8 | runtime error exits 2 | `_cli.py` | killed | `test_cli.py::test_get_missing_key_reports_an_error` |
| X9 | stdout not reconfigured to utf-8 | `_cli.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| X10 | usage error message unbounded | `_cli.py` | killed | `test_hostile.py::test_the_cli_does_not_echo_huge_arguments` |
| M1 | convert: 007 inferred as int | `_commands.py` | killed | `test_validation.py::test_convert_keeps_unusual_numbers_as_text[007]` |
| M2 | convert: yes/no inferred as bool | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M3 | set auto: unsafe bare value kept bare | `_commands.py` | killed | `test_validation.py::test_set_auto_quotes_a_value_that_looks_quoted` |
| M4 | set auto: bare replacement drops comments | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M5 | fmt/convert -o: no CRLF | `_commands.py` | killed | `test_cli_edit.py::test_fmt_writes_crlf_to_a_file` |
| M6 | set -o ignored, file rewritten in place | `_commands.py` | killed | `test_cli_edit.py::test_set_with_types_and_output` |
| M7 | json --section missing: no friendly check | `_commands.py` | killed | `test_cli_edit.py::test_unknown_section_is_an_error` |
| M8 | get --posix inverted | `_commands.py` | killed | `test_cli.py::test_get_decodes_a_path` |
| M9 | json: ensure_ascii True | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M10 | convert: interpolation on | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M11 | convert: keys lower-cased | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M12 | set --posix inverted | `_commands.py` | killed | `test_cli_edit.py::test_set_with_types_and_output` |
| M13 | convert: 1.50 inferred as text (float rule dropped) | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M14 | get: missing key check dropped (KeyError path) | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
| M15 | set --type str ignored, auto behaviour | `_commands.py` | survived, then killed | new contract in `test_mutation_cli_contracts.py` |
### Round 2 (15440fe)

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| C3 | to_bool: strips every whitespace, not only space/tab | `_coerce.py` | killed | `test_mutation_contracts.py::test_to_bool_trims_only_spaces_and_tabs` |
| K2 | short: boundary off by one (<= becomes <) | `_check.py` | killed | `test_mutation_contracts.py::test_error_message_quotes_exactly_forty_characters_in_full` |
| K4 | need_str: returns str subclass instance as is | `_check.py` | killed | `test_hostile_more.py::test_plain_str_comes_back_even_for_a_str_subclass` |
| K5 | type_name: no truncation of long type names | `_check.py` | killed | `test_mutation_contracts.py::test_type_error_message_bounds_a_huge_type_name` |
| N4 | make_entry: str(value) for ints (IntEnum override leaks) | `_entry.py` | killed | `test_mutation_contracts.py::test_int_subclass_is_written_by_its_number_not_its_str` |
| N6 | Entry: comments may be a list | `_entry.py` | killed | `test_mutation_contracts.py::test_entry_refuses_a_list_of_comments` |
| P2 | parse: lone quote char treated as empty quoted string (>=1) | `_parse.py` | killed | `test_labview_more.py::test_a_string_lookup_agrees_with_labview_or_is_a_listed_difference[9]` |
| P10 | parse: repeated-section header comments not merged (last block wins) | `_parse.py` | killed | `test_mutation_contracts.py::test_repeated_section_merges_its_header_comments_in_order` |
| P12 | parse: default eol for no-newline input is CRLF | `_parse.py` | killed | `test_mutation_contracts.py::test_input_without_any_line_break_gets_lf_for_new_lines` |
| L2 | split_lines: empty final line appended (< becomes <=) | `_layout.py` | killed | `test_mutation_contracts.py::test_new_trailing_comment_after_final_newline_adds_no_blank_line` |
| V1 | check_section: CR not refused | `_validate.py` | killed | `test_mutation_contracts.py::test_section_name_with_carriage_return_is_refused` |
| V3 | check_key: tab edge whitespace not refused | `_validate.py` | killed | `test_mutation_contracts.py::test_key_with_edge_tab_is_refused` |
| V8 | check_comments: '/' accepted as comment start | `_validate.py` | killed | `test_mutation_contracts.py::test_comment_must_start_with_semicolon_or_hash` |
| G2 | remove: unnamed section dropped even with header comments | `_config.py` | killed | `test_mutation_contracts.py::test_removing_last_headerless_key_keeps_section_with_comments` |
| W4 | edited key uses layout eol, not its own | `_lossless.py` | killed | `test_mutation_contracts.py::test_edited_key_keeps_its_own_line_ending` |
| W5 | new section: blank line even at start of output | `_lossless.py` | killed | `test_mutation_contracts.py::test_new_section_in_empty_parsed_text_has_no_leading_blank_line` |
| W7 | kept_keys: shadowed items counted | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| W15 | new key comments not written | `_lossless.py` | killed | `test_mutation_contracts.py::test_new_key_in_parsed_config_keeps_its_comments` |
| I3 | save: CR line ending refused | `_io.py` | killed | `test_mutation_contracts.py::test_save_accepts_a_bare_cr_line_ending` |
| X5 | broken pipe exits 0 | `_cli.py` | killed | `test_mutation_cli_contracts.py::test_a_closed_pipe_exits_one` |
| X9 | stdout not reconfigured to utf-8 | `_cli.py` | killed | `test_mutation_cli_contracts.py::test_output_is_utf8_whatever_the_pipe_encoding` |
| M2 | convert: yes/no inferred as bool | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_convert_infers_only_true_false_ints_and_plain_decimals` |
| M4 | set auto: bare replacement drops comments | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_set_auto_keeps_the_comment_of_a_bare_key` |
| M9 | json: ensure_ascii True | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_json_keeps_non_ascii_text_readable` |
| M10 | convert: interpolation on | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_convert_infers_only_true_false_ints_and_plain_decimals` |
| M11 | convert: keys lower-cased | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_convert_infers_only_true_false_ints_and_plain_decimals` |
| M13 | convert: 1.50 inferred as text (float rule dropped) | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_convert_infers_only_true_false_ints_and_plain_decimals` |
| M14 | get: missing key check dropped (KeyError path) | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_get_names_the_missing_section` |
| M15 | set --type str ignored, auto behaviour | `_commands.py` | killed | `test_mutation_cli_contracts.py::test_set_type_str_quotes_even_a_bare_key` |
| P21 | bare ';' value: blanks before ';' not trimmed | `_parse.py` | killed | `test_case_and_blocks.py::test_typed_getters_stop_at_a_bare_semicolon_as_labview_does` |
| P22 | bare ';' value: split at last ';' instead of first | `_parse.py` | killed | `test_labview_more.py::test_a_string_lookup_agrees_with_labview_or_is_a_listed_difference[18]` |
| P23 | bare ';' value: blanks after comment trimmed (branch dropped) | `_parse.py` | killed | `test_hostile.py::test_a_bare_semicolon_reads_and_writes_as_labview_does` |
| P25 | key line prefix excludes blanks after '=' | `_parse.py` | killed | `test_cli_edit.py::test_set_auto_keeps_a_quoted_value_quoted` |
| P26 | key name stripped of every whitespace, not only space/tab | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| P27 | section names not case-folded (case variants are separate sections) | `_parse.py` | killed | `test_case_and_blocks.py::test_a_section_repeated_in_other_case_merges_into_the_first_spelling` |
| P28 | repeated key recorded by exact spelling (case repeats not shadowed, last wins) | `_parse.py` | killed | `test_case_and_blocks.py::test_a_key_repeated_in_other_case_is_a_repeat_and_the_first_wins` |
| P29 | shadowed line keeps its own spelling, not the first one | `_parse.py` | killed | `test_case_and_blocks.py::test_a_key_repeated_in_other_case_is_a_repeat_and_the_first_wins` |
| P30 | header comments recorded even when empty | `_parse.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| P32 | trailing comments dropped | `_parse.py` | killed | `test_comments.py::test_trailing_comment_is_kept` |
| P34 | header needs no closing ']' ('[S] ; note' is a header) | `_parse.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| W21 | first block never closed: new keys go to the last block | `_lossless.py` | killed | `test_case_and_blocks.py::test_a_new_key_goes_into_the_first_block_labview_reads[[S]\nk=1\n[s]\nj=2\n-[S]\nk=1\nn` |
| W22 | later header of a closed section counts as its end | `_lossless.py` | killed | `test_case_and_blocks.py::test_a_new_key_goes_into_the_first_block_labview_reads[[S]\nk=1\n[s]\nj=2\n-[S]\nk=1\nn` |
| W23 | keys of a later block count as the first block's end | `_lossless.py` | killed | `test_case_and_blocks.py::test_a_new_key_goes_into_the_first_block_labview_reads[[S]\nk=1\n[s]\nj=2\n-[S]\nk=1\nn` |
| W24 | done_headers never recorded: edited repeated comments written twice | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| W25 | edited bare ';' value keeps the source trailing blanks | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| W26 | quoting change alone not rewritten | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| W27 | kept_keys ignores quoting (unquoted unsafe value skips check) | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| W28 | unnamed section always emitted at the top | `_lossless.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| W29 | no [] line for new unnamed-section comments | `_lossless.py` | killed | `test_validation.py::test_header_comments_of_the_unnamed_section_keep_a_bracket_line` |
| W32 | _join: every line gets the layout eol | `_lossless.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| W36 | edited comments lose the blank lines among them | `_lossless.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| V21 | is_bare_safe: leading blanks accepted | `_validate.py` | killed | `test_validation.py::test_dump_refuses_a_bare_value_that_would_change[` |
| V22 | is_bare_safe: blank before first ';' accepted | `_validate.py` | killed | `test_hostile.py::test_a_bare_semicolon_reads_and_writes_as_labview_does` |
| V23 | is_bare_safe: trailing blanks refused even after ';' | `_validate.py` | killed | `test_hostile.py::test_a_bare_semicolon_reads_and_writes_as_labview_does` |
| V25 | check_comments: trailing blanks accepted | `_validate.py` | killed | `test_review_contracts.py::test_a_comment_parse_would_trim_is_refused[;` |
| V26 | dump: case-colliding section names accepted | `_validate.py` | killed | `test_case_and_blocks.py::test_names_that_differ_only_in_case_are_refused_on_dump[<lambda>1]` |
| V27 | dump: case-colliding key names accepted | `_validate.py` | killed | `test_case_and_blocks.py::test_names_that_differ_only_in_case_are_refused_on_dump[<lambda>0]` |
| V29 | check_key: every '[' key with a bare value refused | `_validate.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| V30 | check_config: header comments not checked | `_validate.py` | killed | `test_mutation_contracts.py::test_comment_must_start_with_semicolon_or_hash` |
| V31 | check_key: CR in key accepted | `_validate.py` | killed | `test_validation.py::test_set_refuses_a_key_that_would_read_back_differently[a\rb]` |
| K21 | fold: Unicode lower() instead of ASCII-only folding | `_check.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| K22 | short: character count dropped from long messages | `_check.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._check]` |
| R21 | typed getters do not stop at a bare ';' | `_reading.py` | killed | `test_case_and_blocks.py::test_typed_getters_stop_at_a_bare_semicolon_as_labview_does` |
| R22 | typed getters stop at ';' inside quotes too | `_reading.py` | killed | `test_case_and_blocks.py::test_typed_getters_stop_at_a_bare_semicolon_as_labview_does` |
| R23 | get_path: tab not mapped back to its \09 code | `_reading.py` | killed | `test_case_and_blocks.py::test_a_stored_path_resolves_its_backslashes_as_labview_does` |
| R24 | get_path: resolves the decoded value, not the stored text | `_reading.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| R25 | get_path: stored text re-escaped for POSIX too | `_reading.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| H21 | relative '..' after '..' pops it (../../x becomes x) | `_path.py` | killed | `test_labview_more.py::test_a_path_reads_as_labview_reads_it_or_is_refused["../../x"]` |
| H22 | '..' above the drive root kept instead of refused | `_path.py` | killed | `test_labview_more.py::test_a_path_reads_as_labview_reads_it_or_is_refused["/C/.."]` |
| H23 | empty relative result not '.' | `_path.py` | killed | `test_labview_more.py::test_a_path_reads_as_labview_reads_it_or_is_refused["."]` |
| H24 | UNC '..' above the share kept, not refused | `_path.py` | killed | `test_labview_more.py::test_a_path_reads_as_labview_reads_it_or_is_refused["//server/share/../x"]` |
| H27 | to_labview_path: drive path not resolved/refused like the reader | `_path.py` | killed | `test_review_contracts.py::test_a_path_above_its_drive_root_is_refused_when_stored[C:\\..]` |
| H28 | stored backslash not a separator | `_path.py` | killed | `test_case_and_blocks.py::test_a_stored_path_resolves_its_backslashes_as_labview_does` |
| H29 | bare '/D' drive root not recognised | `_path.py` | killed | `test_labview_captures.py::test_a_path_reads_as_labview_reads_it_or_is_refused["/C"]` |
| H30 | relative path resolved as rooted (leading '..' refused) | `_path.py` | killed | `test_handwritten_fixtures.py::test_stored_paths_decode_to_the_right_files` |
| I21 | write_text: file opened before encoding (truncates on failure) | `_io.py` | killed | `test_review_contracts.py::test_a_failed_save_leaves_the_file_untouched[\u4e2d\u6587-cp1252]` |
| I22 | load: int path taken as a file descriptor | `_io.py` | killed | `test_review_contracts.py::test_load_and_save_refuse_paths_of_other_types[1]` |
| I23 | need_path: bytes os.PathLike accepted | `_io.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| I25 | save: forced ending replaces only LF ('\r' and CRLF kept) | `_io.py` | killed | `test_io.py::test_an_explicit_line_ending_is_forced_on_a_loaded_file` |
| I26 | load: encoding type unchecked | `_io.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| I27 | save: encoding type check dropped (encode raises TypeError anyway) | `_io.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| N21 | Entry keeps a str subclass value | `_entry.py` | killed | `test_review_contracts.py::test_names_are_stored_as_plain_str` |
| N22 | Entry keeps str subclass comments | `_entry.py` | killed | `test_review_contracts.py::test_names_are_stored_as_plain_str` |
| N23 | huge int raises ValueError, not LvConfigError | `_entry.py` | killed | `test_review_contracts.py::test_an_integer_too_long_to_write_is_an_lvconfig_error` |
| N24 | float subclass repr override leaks | `_entry.py` | killed | `test_hostile.py::test_subclasses_are_written_as_the_value_they_hold` |
| N25 | make_entry str: no str.__str__ (Entry normalises anyway) | `_entry.py` | equivalent | equivalent: Entry already keeps a plain str copy |
| D21 | empty unnamed section written with no [] line | `_dump.py` | killed | `test_review_contracts.py::test_an_empty_unnamed_section_survives_a_round_trip` |
| D22 | empty blocks kept in canonical join | `_dump.py` | equivalent | equivalent: section_lines never returns an empty list |
| M22 | convert: very long digit runs inferred as int | `_commands.py` | killed | `test_review_contracts.py::test_convert_keeps_a_number_too_long_for_python_as_text` |
| M23 | convert: inference without strip | `_commands.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| M24 | convert: text value returned stripped | `_commands.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| M27 | convert: input read in the locale encoding | `_commands.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| M28 | fmt: lossless instead of canonical | `_commands.py` | killed | `test_cli_edit.py::test_fmt_prints_the_canonical_form` |
| M31 | set: --encoding ignored on write | `_commands.py` | killed | `test_review_contracts.py::test_a_failed_cli_set_leaves_the_file_untouched` |
| M34 | fmt/convert -o: --encoding ignored on write | `_commands.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| X21 | configparser.Error not handled (traceback) | `_cli.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
| X22 | stderr not reconfigured to utf-8 | `_cli.py` | survived, then killed | new contract in `test_mutation_contracts_two.py` |
### Round 3 (11cd75d)

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| W7 | kept_keys: shadowed items counted | `_blocks.py` | equivalent | equivalent: kept only skips the bare read-back check, and every bare value parse can produce reads back when rebuilt (100k fuzz, 0 failures; the shadow rule is otherwise guarded by F9s test) |
| W24 | done_headers never recorded: edited repeated comments written twice | `_lossless.py` | killed | `test_mutation_contracts_two.py::test_edited_comments_of_a_repeated_section_are_written_once` |
| W25 | edited bare ';' value keeps the source trailing blanks | `_lossless.py` | killed | `test_mutation_contracts_two.py::test_an_edited_bare_value_with_a_semicolon_drops_the_source_trailing_blanks` |
| W26 | quoting change alone not rewritten | `_lossless.py` | killed | `test_mutation_contracts_two.py::test_changing_only_the_quoting_rewrites_the_line` |
| W27 | kept_keys ignores quoting | `_blocks.py` | killed | `test_mutation_contracts_two.py::test_unquoting_a_parsed_value_is_checked_like_any_bare_value` |
| W36 | edited comments lose the blank lines among them | `_lossless.py` | killed | `test_mutation_contracts_two.py::test_edited_key_comments_keep_the_blank_lines_around_them` |
| R24 | get_path: resolves the decoded value, not the stored text | `_reading.py` | killed | `test_case_and_blocks.py::test_a_stored_path_resolves_its_backslashes_as_labview_does` |
| R25 | get_path: stored text used for POSIX too | `_reading.py` | killed | `test_mutation_contracts_two.py::test_get_path_returns_a_posix_value_as_stored` |
| I23 | need_path: bytes os.PathLike accepted | `_io.py` | killed | `test_mutation_contracts_two.py::test_a_bytes_path_like_is_refused` |
| I26 | load: encoding type unchecked | `_io.py` | killed | `test_mutation_contracts_two.py::test_load_refuses_an_encoding_that_is_not_a_str` |
| I27 | save: encoding type check dropped | `_io.py` | killed | `test_mutation_contracts_two.py::test_save_checks_its_arguments_before_the_config` |
| M23 | convert: inference without strip | `_commands.py` | killed | `test_mutation_contracts_two.py::test_convert_infers_a_number_that_starts_on_a_continuation_line` |
| M24 | convert: text value returned stripped | `_commands.py` | killed | `test_mutation_contracts_two.py::test_convert_keeps_text_that_starts_on_a_continuation_line` |
| M27 | convert: input read in the locale encoding | `_commands.py` | killed | `test_mutation_contracts_two.py::test_convert_reads_and_writes_in_the_given_encoding` |
| M34 | fmt/convert -o: --encoding ignored on write | `_commands.py` | killed | `test_mutation_contracts_two.py::test_convert_reads_and_writes_in_the_given_encoding` |
| X21 | configparser.Error not handled | `_cli.py` | killed | `test_mutation_contracts_two.py::test_convert_reports_a_malformed_plain_ini_as_an_error` |
| X22 | stderr not reconfigured to utf-8 | `_cli.py` | killed | `test_mutation_contracts_two.py::test_errors_are_utf8_whatever_the_pipe_encoding` |
| F1 | is_quoted: a lone quote counts as quoted | `_stored.py` | killed | `test_labview_more.py::test_a_string_lookup_agrees_with_labview_or_is_a_listed_difference[9]` |
| F2 | is_quoted: single quotes not recognised | `_stored.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| F3 | body_of: quoted value with ';' keeps trailing blanks | `_stored.py` | killed | `test_labview_third.py::test_a_found_value_is_labviews_value[172]` |
| F4 | body_of: blanks after a comment trimmed | `_stored.py` | killed | `test_hostile.py::test_a_bare_semicolon_reads_and_writes_as_labview_does` |
| F5 | read: blanks before a bare ';' kept | `_stored.py` | killed | `test_case_and_blocks.py::test_typed_getters_stop_at_a_bare_semicolon_as_labview_does` |
| F6 | read: quoted value not unescaped | `_stored.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._parse]` |
| F7 | read: bare value not unescaped | `_stored.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| F8 | stored: remembered text ignored | `_stored.py` | killed | `test_case_and_blocks.py::test_a_stored_path_resolves_its_backslashes_as_labview_does` |
| F9 | stored: bare tab not written as \09 | `_stored.py` | killed | `test_mutation_contracts_two.py::test_a_later_repeated_line_does_not_vouch_for_a_new_bare_value` |
| F10 | stored: quoted tab also written as \09 | `_stored.py` | killed | `test_labview_captures.py::test_a_string_is_written_exactly_as_labview_writes_it[9]` |
| F11 | render: bare values quoted | `_stored.py` | killed | `test_case_and_blocks.py::test_a_key_repeated_in_other_case_is_a_repeat_and_the_first_wins` |
| F12 | reads_back: quoting ignored | `_stored.py` | equivalent | equivalent: reads_back is only called for bare entries; a bare render that reads as quoted loses its two outer quotes, so the value always differs too |
| F13 | remember: stored text not attached | `_stored.py` | killed | `test_case_and_blocks.py::test_a_stored_path_resolves_its_backslashes_as_labview_does` |
| F14 | first block never closes | `_blocks.py` | killed | `test_case_and_blocks.py::test_a_new_key_goes_into_the_first_block_labview_reads[[S]\nk=1\n[s]\nj=2\n-[S]\nk=1\nn` |
| F15 | closes the new section instead of the previous one | `_blocks.py` | killed | `test_case_and_blocks.py::test_a_new_key_goes_into_the_first_block_labview_reads[[A]\na=1\n[B]\nx=1\n[A]\nb=2\n-[A]\na=1\nn` |
| F16 | first_block_ends: last block used | `_blocks.py` | killed | `test_case_and_blocks.py::test_a_new_key_goes_into_the_first_block_labview_reads[[S]\nk=1\n[s]\nj=2\n-[S]\nk=1\nn` |
| F17 | moved_keys: first-block edits counted as moved | `_blocks.py` | killed | `test_case_and_blocks.py::test_a_key_repeated_in_other_case_is_a_repeat_and_the_first_wins` |
| F18 | moved_keys: shadowed later lines counted | `_blocks.py` | killed (new contract) | `test_mutation_contracts_three.py::test_a_key_repeated_in_a_later_block_of_its_section_is_not_written_twice` |
| F21 | key name stripped of every whitespace | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| F22 | header names not case folded | `_parse.py` | killed | `test_case_and_blocks.py::test_a_section_repeated_in_other_case_merges_into_the_first_spelling` |
| F23 | repeated key detection case sensitive | `_parse.py` | killed | `test_case_and_blocks.py::test_an_edit_of_a_key_in_a_later_block_goes_into_the_first_block` |
| F24 | header must end in ']' | `_parse.py` | killed | `test_case_and_blocks.py::test_a_line_starting_with_a_bracket_and_holding_one_is_a_header[[T]` |
| F25 | header name cut at first ']' | `_parse.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| F26 | header text stripped on both sides | `_parse.py` | killed | `test_labview_more.py::test_a_string_lookup_agrees_with_labview_or_is_a_listed_difference[38]` |
| F27 | default eol CRLF for a file with no newline | `_parse.py` | killed | `test_mutation_contracts.py::test_input_without_any_line_break_gets_lf_for_new_lines` |
| F28 | final_eol ignores a missing final newline | `_parse.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| F29 | BOM not recognised | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| F30 | comments recorded unstripped | `_parse.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| F32 | removed section header still written | `_lossless.py` | killed | `test_lossless.py::test_removing_a_section_drops_every_block_of_it` |
| F33 | edited header comments never written | `_lossless.py` | killed | `test_lossless.py::test_edited_header_and_trailing_comments_are_written` |
| F34 | moved key rewritten in place too | `_lossless.py` | killed | `test_case_and_blocks.py::test_an_edit_of_a_key_in_a_later_block_goes_into_the_first_block` |
| F35 | removed key keeps its comment lines | `_lossless.py` | killed | `test_docs.py::test_document_examples_run_and_print_what_they_show[GUIDE.md]` |
| F36 | moved key comments duplicated | `_lossless.py` | superseded | the moved key's comments are now written with it, so the config reads back equal (lens c round 3); pinned by `test_case_and_blocks.py::test_a_moved_edit_keeps_its_comments_so_the_config_reads_back_equal` |
| F37 | blank line before a new unnamed section | `_lossless.py` | equivalent | equivalent: new_section("") runs only before anything is emitted; the final loop skips "" |
| F38 | moved keys never written to the first block | `_lossless.py` | killed | `test_case_and_blocks.py::test_an_edit_of_a_key_in_a_later_block_goes_into_the_first_block` |
| F39 | edited trailing comments ignored | `_lossless.py` | killed | `test_lossless.py::test_edited_header_and_trailing_comments_are_written` |
| F40 | missing final newline gets one | `_lossless.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| F41 | mixed line endings normalised | `_lossless.py` | killed | `test_fuzz.py::test_any_text_parses_or_raises_a_parse_error_and_round_trips` |
| F42 | no BOM protection in lossless output | `_lossless.py` | killed (new contract) | `test_mutation_contracts_three.py::test_a_new_headerless_key_starting_with_a_bom_character_survives_a_lossless_dump` |
| F43 | section name with CR accepted | `_validate.py` | killed | `test_mutation_contracts.py::test_section_name_with_carriage_return_is_refused` |
| F44 | key with edge tab accepted | `_validate.py` | killed | `test_mutation_contracts.py::test_key_with_edge_tab_is_refused` |
| F45 | '[' key with ']' only in value accepted | `_validate.py` | killed | `test_fuzz.py::test_any_config_built_in_code_reads_back_as_itself` |
| F46 | kept keys re-checked | `_validate.py` | equivalent | equivalent: kept entries equal a parsed bare value, and every parsed bare value reads back (100k fuzz, 0 failures) |
| F47 | comment with trailing blanks accepted | `_validate.py` | killed | `test_review_contracts.py::test_a_comment_parse_would_trim_is_refused[;` |
| F48 | names differing only in case accepted | `_validate.py` | killed | `test_case_and_blocks.py::test_names_that_differ_only_in_case_are_refused_on_dump[<lambda>0]` |
| F49 | header comments for missing section accepted | `_validate.py` | killed | `test_validation.py::test_dump_refuses_header_comments_for_a_missing_section` |
| F50 | key starting with '#' accepted | `_validate.py` | killed | `test_validation.py::test_set_refuses_a_key_that_would_read_back_differently[#k]` |
| F51 | typed read of bare value not cut at ';' | `_reading.py` | killed | `test_case_and_blocks.py::test_typed_getters_stop_at_a_bare_semicolon_as_labview_does` |
| F52 | typed read of quoted value cut at ';' | `_reading.py` | killed | `test_case_and_blocks.py::test_typed_getters_stop_at_a_bare_semicolon_as_labview_does` |
| F53 | typed read uses decoded value | `_reading.py` | killed | `test_labview_third.py::test_a_boolean_is_labviews_or_refused[TRUE\\09-None]` |
| F54 | get: default unchecked | `_reading.py` | killed | `test_review_contracts.py::test_get_refuses_a_default_that_is_not_a_str` |
| F55 | get: default ignored | `_reading.py` | killed | `test_config.py::test_get_returns_the_default_when_missing` |
| F56 | '.' parts kept | `_path.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._path]` |
| F57 | relative '..' collapses another '..' | `_path.py` | killed | `test_labview_more.py::test_a_path_reads_as_labview_reads_it_or_is_refused["../../x"]` |
| F58 | UNC without share accepted | `_path.py` | killed | `test_labview_captures.py::test_a_path_reads_as_labview_reads_it_or_is_refused["//server"]` |
| F59 | drive-relative path accepted | `_path.py` | killed | `test_cli_edit.py::test_set_refuses_a_drive_relative_path` |
| F60 | ':' outside a drive accepted | `_path.py` | killed | `test_labview_third.py::test_a_path_is_labviews_or_refused[":x"]` |
| F61 | control characters accepted in to_labview_path | `_path.py` | killed | `test_review_contracts.py::test_a_path_with_a_control_character_is_refused_when_stored[C:\x07\tb]` |
| F62 | bare drive root written as /C/ | `_path.py` | killed | `test_path.py::test_bare_drive_stores_without_a_trailing_slash` |
| F63 | malformed /C:/ drive accepted | `_path.py` | killed (new contract) | `test_mutation_contracts_three.py::test_a_malformed_drive_is_refused_as_malformed_not_as_a_posix_path` |
| F64 | native UNC accepted in from_labview_path | `_path.py` | killed | `test_promises.py::test_path_promise` |
| F65 | drive pattern without DOTALL | `_path.py` | killed (new contract) | `test_mutation_contracts_three.py::test_a_drive_path_holding_a_line_break_still_resolves_as_a_drive_path` |
| F66 | UNC '..' above the share allowed | `_path.py` | killed | `test_labview_more.py::test_a_path_reads_as_labview_reads_it_or_is_refused["//server/share/../x"]` |
| F67 | built config saved with LF | `_io.py` | killed | `test_docs.py::test_module_doctests_pass[lvconfig._io]` |
| F68 | CRLF split into two endings on save | `_io.py` | killed | `test_io.py::test_an_explicit_line_ending_is_forced_on_a_loaded_file` |
| F69 | load translates newlines | `_io.py` | killed | `test_cli_edit.py::test_set_edits_one_line_in_place` |
| F70 | temporary file left behind on failure | `_io.py` | killed | `test_write_safety.py::test_a_save_that_cannot_replace_the_file_leaves_it_whole` |
| F71 | temporary file in the system temp folder | `_io.py` | killed (new contract) | `test_mutation_contracts_three.py::test_a_save_replaces_the_target_from_a_temporary_file_in_its_own_folder` |
| F72 | line_ending CR refused | `_io.py` | killed | `test_mutation_contracts.py::test_save_accepts_a_bare_cr_line_ending` |
| F73 | short: 40 characters cut | `_check.py` | killed | `test_mutation_contracts.py::test_error_message_quotes_exactly_forty_characters_in_full` |
| F74 | type_name not bounded | `_check.py` | killed | `test_mutation_contracts.py::test_type_error_message_bounds_a_huge_type_name` |
| F75 | fold misses the first Latin-1 capital | `_check.py` | killed (new contract) | `test_mutation_contracts_three.py::test_every_latin1_capital_folds_when_names_are_compared` |
| F76 | need_str returns a str subclass as is | `_check.py` | killed | `test_hostile_more.py::test_plain_str_comes_back_even_for_a_str_subclass` |
| F77 | fold lower-cases all of Unicode | `_check.py` | killed (new contract) | `test_mutation_contracts_three.py::test_capitals_beyond_latin1_do_not_fold` |
## Decisions for the maintainer

- 1.0.0 follows what LabVIEW 2026 itself reads and writes, proven against three capture runs,
  rather than 0.3's own conventions. The behaviour changes are many (escaping, first-key
  wins, case folding, bare `;` comments, header lines, typed reads of the stored text, path
  resolution, the canonical layout with `key = value` and no final newline); CHANGELOG and
  the GUIDE's upgrade section list them.
- Where LabVIEW silently reads something lvconfig cannot represent faithfully (partial
  numbers and booleans, paths that name another file, lines with no `=`), lvconfig raises
  instead. Integers keep every digit where LabVIEW's Read Key (I32) clamps to 32 bits. Every
  difference is listed in GUIDE.md and pinned by a test.
- Section and key lookups through the API stay exact-case; only reading a file folds case
  as LabVIEW does. `dump` refuses names that differ only in case.
- `load` and `save` keep UTF-8 as the default encoding; LabVIEW uses the system code page,
  which the guide tells users to pass.
- `save` now writes through a temporary file in the target's folder and replaces the
  target, so the saved file is a new file (links and permissions are not carried over).
- The LabVIEW captures ship in the sdist as test fixtures: the author's and reviewers'
  inputs with LabVIEW's output, plus 189 bytes that LabVIEW's shipped example writes with
  its default front panel; no NI text. NI's own `.ini` excerpts stay local (manifest only).
- 0.3.0 and 0.3.1 were never published; CHANGELOG marks them so, and the upgrade notes
  cover 0.2.0 to 1.0.0.
- GUIDE.md and this report are longer than 200 lines; the 200-line rule is applied to
  source files.
- The README links to GUIDE.md and CHANGELOG.md on `main`, so publish after the merge.
- Branch history contains intermediate states later rewritten; a squash merge keeps `main`
  to the final state.
