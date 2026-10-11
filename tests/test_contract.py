import importlib.resources

import lvconfig

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "Config",
    "Entry",
    "LvConfigError",
    "LvParseError",
    "dump",
    "escape",
    "from_labview_path",
    "load",
    "parse",
    "save",
    "to_bool",
    "to_float",
    "to_int",
    "to_labview_path",
    "unescape",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvconfig.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvconfig.__all__:
        assert hasattr(lvconfig, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvconfig.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvconfig").joinpath("py.typed").is_file()


def test_the_cli_entry_point_is_callable() -> None:
    from lvconfig._cli import main

    assert callable(main)
