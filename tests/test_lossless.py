"""A parsed config dumps back byte for byte, and edits touch only their own lines."""

import pytest

from lvconfig import Config, dump, parse

MESSY = (
    "\ufeff; header\r\n"
    "[A]\r\n"
    '  name = "Rig"   \r\n'
    "\r\n"
    "# about flag\r\n"
    "flag=TRUE\r\n"
    "[B]\r\n"
    "x= 1\r\n"
    "[A]\r\n"
    "late = 'q'\r\n"
    "; tail"
)


@pytest.mark.parametrize(
    "text",
    [
        MESSY,
        "",
        "\n\n",
        "[A]\nx=1",
        "[A]\rx=1\r",
        "[A]\nx=1\r\ny=2\n",
        "k=1\n[A]\nk=2\n",
        "[A]\nx=1\nx=2\n",
        "[A]\nempty=\nspaces=   \n",
    ],
)
def test_dump_reproduces_the_source_exactly(text: str) -> None:
    assert dump(parse(text)) == text


def test_editing_a_value_rewrites_only_its_line() -> None:
    config = parse(MESSY)
    config.set("A", "name", "Rack")
    assert dump(config) == MESSY.replace('"Rig"', '"Rack"')


def test_an_unquoted_edit_keeps_the_original_spacing() -> None:
    config = parse(MESSY)
    config.set("B", "x", 2)
    assert dump(config) == MESSY.replace("x= 1", "x= 2")


def test_setting_the_same_value_changes_nothing() -> None:
    config = parse(MESSY)
    config.set("A", "flag", True)
    assert dump(config) == MESSY


def test_removing_a_key_drops_its_comment_lines() -> None:
    config = parse(MESSY)
    config.remove("A", "flag")
    assert dump(config) == MESSY.replace("# about flag\r\nflag=TRUE\r\n", "")


def test_removing_a_section_drops_every_block_of_it() -> None:
    config = parse(MESSY)
    config.remove_section("A")
    assert dump(config) == "\ufeff[B]\r\nx= 1\r\n; tail"


def test_a_new_key_goes_after_the_last_key_of_its_section() -> None:
    config = parse("[A]\nx=1\n\n[B]\ny=2\n")
    config.set("A", "z", 3)
    assert dump(config) == "[A]\nx=1\nz=3\n\n[B]\ny=2\n"


def test_a_new_section_is_appended_with_the_file_line_ending() -> None:
    config = parse("[A]\r\nx=1")
    config.set("New", "on", False)
    assert dump(config) == "[A]\r\nx=1\r\n\r\n[New]\r\non=FALSE"


def test_a_new_headerless_key_goes_at_the_top() -> None:
    config = parse("[A]\nx=1\n")
    config.set("", "top", 1)
    assert dump(config) == "top=1\n[A]\nx=1\n"
    assert parse(dump(config)) == config


def test_edited_key_comments_replace_the_old_ones() -> None:
    config = parse("[A]\n; old\nx=1\n")
    entry = config.sections["A"]["x"]
    config.sections["A"]["x"] = type(entry)(entry.value, entry.quoted, ("; new",))
    assert dump(config) == "[A]\n; new\nx=1\n"


def test_edited_header_and_trailing_comments_are_written() -> None:
    config = parse("; top\n[A]\nx=1\n; end\n")
    config.header_comments["A"] = ("; changed",)
    config.trailing_comments = ()
    assert dump(config) == "; changed\n[A]\nx=1\n"


def test_a_redefined_key_updates_its_last_line_only() -> None:
    config = parse("[A]\nx=1\nx=2\n")
    assert config.get_int("A", "x") == 2
    config.set("A", "x", 5)
    assert dump(config) == "[A]\nx=1\nx=5\n"


def test_normalize_writes_the_canonical_form() -> None:
    config = parse('[A]\n  x = 1  \n\n\n[B]\ny = "v"\n')
    assert dump(config, normalize=True) == '[A]\nx=1\n\n[B]\ny="v"\n'


def test_canonical_form_puts_headerless_keys_first() -> None:
    config = Config()
    config.set("A", "x", 1)
    config.set("", "top", 2)
    assert dump(config) == "top=2\n\n[A]\nx=1\n"
    assert parse(dump(config)) == config


def test_forgetting_the_layout_gives_the_canonical_form() -> None:
    config = parse("[A]\n x = 1\n")
    config.layout = None
    assert dump(config) == "[A]\nx=1\n"


def test_layout_takes_no_part_in_equality() -> None:
    assert parse("[A]\n x = 1 \n") == parse("[A]\nx=1")


@pytest.mark.parametrize(
    ("value", "token"), [(float("inf"), "Inf"), (float("-inf"), "-Inf"), (float("nan"), "NaN")]
)
def test_special_floats_use_labview_spelling(value: float, token: str) -> None:
    config = Config()
    config.set("N", "v", value)
    assert dump(config) == f"[N]\nv={token}\n"
