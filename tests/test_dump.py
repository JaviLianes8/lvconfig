from lvconfig import Config, dump


def test_dump_quotes_and_escapes_a_string() -> None:
    config = Config()
    config.set("General", "name", 'Rig "A"\r')
    assert dump(config) == '[General]\nname="Rig \\22A\\22\\0D"\n'


def test_dump_writes_booleans_as_bare_tokens() -> None:
    config = Config()
    config.set("General", "enabled", True)
    config.set("General", "muted", False)
    assert dump(config) == "[General]\nenabled=TRUE\nmuted=FALSE\n"


def test_dump_writes_numbers_without_quotes() -> None:
    config = Config()
    config.set("Nums", "count", 7)
    config.set("Nums", "ratio", 0.5)
    assert dump(config) == "[Nums]\ncount=7\nratio=0.5\n"


def test_dump_stores_a_path_in_labview_form() -> None:
    config = Config()
    config.set_path("Paths", "log", "C:\\Temp\\log.txt")
    assert dump(config) == '[Paths]\nlog="/C/Temp/log.txt"\n'


def test_dump_separates_sections_with_a_blank_line() -> None:
    config = Config()
    config.set("A", "x", 1)
    config.set("B", "y", 2)
    assert dump(config) == "[A]\nx=1\n\n[B]\ny=2\n"


def test_empty_config_dumps_to_an_empty_string() -> None:
    assert dump(Config()) == ""
