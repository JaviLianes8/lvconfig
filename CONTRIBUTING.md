# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/lvconfig/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Format behaviour is checked against the
  hand-written fixtures in `tests/fixtures/handwritten/`. Keep them byte-exact: they
  are stored with `CRLF` (see `.gitattributes`). Never commit files copied from a
  LabVIEW install: `python scripts/capture_ni.py` writes the NI excerpts the tests can
  also use into the gitignored `tests/fixtures/ni/`. The end-to-end test installs the
  package into a throwaway virtual environment and runs the real `lvconfig` script.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
