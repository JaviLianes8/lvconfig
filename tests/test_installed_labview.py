"""Round-trip every configuration file of a local LabVIEW install, when one exists.

Skipped on machines without LabVIEW. Point ``LVCONFIG_LABVIEW_DIR`` at another
installation folder to check a different version.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from lvconfig import dump, parse

_DEFAULT = "C:/Program Files/National Instruments/LabVIEW 2026"
ROOT = Path(os.environ.get("LVCONFIG_LABVIEW_DIR", _DEFAULT))
FILES = sorted(ROOT.rglob("*.ini")) if ROOT.is_dir() else []


@pytest.mark.skipif(not FILES, reason="no LabVIEW installation found")
def test_every_installed_ini_round_trips_byte_for_byte() -> None:
    failures = []
    for path in FILES:
        data = path.read_bytes()
        # latin-1 maps every byte to one character, so any code page survives.
        config = parse(data.decode("latin-1"))
        if dump(config).encode("latin-1") != data:
            failures.append(str(path.relative_to(ROOT)))
        assert parse(dump(config, normalize=True)) == config
    assert failures == []
