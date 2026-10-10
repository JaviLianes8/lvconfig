from lvconfig import Config, dump, parse


def test_parse_dump_parse_is_stable() -> None:
    config = Config()
    config.set("General", "name", 'Rig "A"\r\nline')
    config.set("General", "enabled", True)
    config.set("General", "retries", 3)
    config.set("General", "threshold", 2.5)
    config.set_path("Paths", "log", "C:\\Temp\\log.txt")

    once = dump(config)
    reparsed = parse(once)
    assert dump(reparsed) == once
    assert reparsed == config


def test_values_survive_a_full_cycle() -> None:
    config = parse(dump_sample())
    assert config.get_str("General", "name") == 'weird\tvalue "q"'
    assert config.get_bool("General", "on") is True
    assert config.get_path("Paths", "data") == "D:\\runs\\today.bin"


def dump_sample() -> str:
    config = Config()
    config.set("General", "name", 'weird\tvalue "q"')
    config.set("General", "on", True)
    config.set_path("Paths", "data", "D:\\runs\\today.bin")
    return dump(config)
