from lvconfig import Config, dump, parse

SAMPLE = """\
; file header note
[General]
; explain the name
name = "Rig"
enabled = TRUE

[Paths]
log = "/C/Temp/log.txt"
; a trailing remark
"""


def test_section_header_comment_is_kept() -> None:
    config = parse(SAMPLE)
    assert config.header_comments["General"] == ("; file header note",)


def test_key_comment_is_kept() -> None:
    config = parse(SAMPLE)
    entry = config.sections["General"]["name"]
    assert entry.comments == ("; explain the name",)


def test_trailing_comment_is_kept() -> None:
    assert parse(SAMPLE).trailing_comments == ("; a trailing remark",)


def test_comments_survive_a_dump() -> None:
    config = parse(SAMPLE)
    reparsed = parse(dump(config))
    assert reparsed == config


def test_dump_writes_comments_above_their_target() -> None:
    config = Config()
    config.set("A", "x", 1)
    config.sections["A"]["x"] = config.sections["A"]["x"].__class__("1", False, ("; note",))
    config.header_comments["A"] = ("; section note",)
    assert dump(config) == "; section note\n[A]\n; note\nx=1\n"
