"""The documentation is executable: doctests, README and GUIDE examples and transcripts run."""

from __future__ import annotations

import configparser
import doctest
import importlib
import inspect
import pkgutil
import re
import shlex
from pathlib import Path

import pytest

import lvconfig
from lvconfig._cli import main

_ROOT = Path(__file__).resolve().parent.parent
_MODULES = ["lvconfig"] + [f"lvconfig.{m.name}" for m in pkgutil.iter_modules(lvconfig.__path__)]
_PYCON = re.compile(r"```pycon\n(.*?)```", re.DOTALL)
_SHELL = re.compile(r"```\n(\$ lvconfig.*?)```", re.DOTALL)
_DOCS = ["README.md", "GUIDE.md"]


@pytest.mark.parametrize("name", _MODULES)
def test_module_doctests_pass(name: str) -> None:
    result = doctest.testmod(importlib.import_module(name))
    assert result.failed == 0


@pytest.mark.parametrize("name", lvconfig.__all__)
def test_every_public_callable_has_a_docstring_with_an_example(name: str) -> None:
    item = getattr(lvconfig, name)
    if inspect.isclass(item) and issubclass(item, Exception):
        assert (item.__doc__ or "").strip(), name
    else:
        assert ">>>" in (item.__doc__ or ""), name


@pytest.mark.parametrize(
    "name", [n for n, _ in inspect.getmembers(lvconfig.Config) if not n.startswith("_")]
)
def test_every_public_method_has_an_example(name: str) -> None:
    member = getattr(lvconfig.Config, name)
    if callable(member):
        assert ">>>" in (member.__doc__ or ""), name


def _run_document(document: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = (_ROOT / document).read_text(encoding="utf-8")
    parser = doctest.DocTestParser()
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS)
    globs: dict[str, object] = {}
    for number, block in enumerate(_PYCON.findall(text)):
        test = parser.get_doctest(block, {}, f"{document}[{number}]", document, 0)
        test.globs = globs  # one namespace per document, as a reader follows it
        runner.run(test, clear_globs=False)
    assert runner.summarize(verbose=False).failed == 0
    for block in _SHELL.findall(text):
        for chunk in block.split("$ lvconfig")[1:]:
            command, _, expected = chunk.partition("\n")
            capsys.readouterr()
            assert main(shlex.split(command, posix=False)) == 0, command
            assert capsys.readouterr().out == expected, command


@pytest.mark.parametrize("document", _DOCS)
def test_document_examples_run_and_print_what_they_show(
    document: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _run_document(document, tmp_path, capsys)


def test_examples_import_only_public_names() -> None:
    for document in _DOCS:
        text = (_ROOT / document).read_text(encoding="utf-8")
        for line in re.findall(r"from lvconfig[\w.]* import [^\n]+", text):
            assert line.startswith("from lvconfig import "), line
            names = line.removeprefix("from lvconfig import ").split(", ")
            assert set(names) <= set(lvconfig.__all__), line


def test_readme_links_are_absolute_and_point_at_the_guide_and_changelog() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)]+)\)", readme)
    assert links and all(link.startswith("https://") for link in links)
    assert any(link.endswith("/GUIDE.md") for link in links)
    assert any(link.endswith("/CHANGELOG.md") for link in links)


def test_the_readme_claims_about_configparser_hold() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string('; note\n[Rig]\nName = "Bench\\0A2\\\\x"\nlog = /C/Temp/log.txt\n')
    assert parser["Rig"]["name"] == '"Bench\\0A2\\\\x"'  # quotes kept, nothing decoded
    assert parser["Rig"]["log"] == "/C/Temp/log.txt"
    assert list(parser["Rig"]) == ["name", "log"]  # key names lower-cased
    import io

    out = io.StringIO()
    parser.write(out)
    assert "; note" not in out.getvalue()


def test_the_changelog_has_a_dated_1_0_0_section() -> None:
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[1\.0\.0\] - \d{4}-\d{2}-\d{2}$", changelog, re.MULTILINE)
