"""Cut the NI configuration file excerpts listed in tests/fixtures/ni/MANIFEST.json.

The excerpts come from files a LabVIEW 2026 install puts on disk, so they are not part
of the repository. Their tests skip until this script has written them. Each excerpt
keeps the source bytes unchanged (CRLF and a missing final newline included) and is
checked against the size and sha256 in the manifest.

    python scripts/capture_ni.py [labview-install-folder]
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ni"
DEFAULT = "C:/Program Files/National Instruments/LabVIEW 2026"


def _excerpt(data: bytes, ranges: list[list[int]] | None, skip: list[int]) -> bytes:
    kept = []
    for number, line in enumerate(data.splitlines(keepends=True), 1):
        if ranges and not any(first <= number <= last for first, last in ranges):
            continue
        if number not in skip:
            kept.append(line)
    return b"".join(kept)


def main(argv: list[str]) -> int:
    root = Path(argv[0] if argv else os.environ.get("LVCONFIG_LABVIEW_DIR", DEFAULT))
    manifest = json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
    failed = 0
    for name, entry in manifest["files"].items():
        source = root / entry["origin"]
        if not source.is_file():
            print(f"{name}: not found at {source}")
            failed += 1
            continue
        body = _excerpt(source.read_bytes(), entry["lines"], entry["skip"])
        digest = hashlib.sha256(body).hexdigest()
        if len(body) != entry["size"] or digest != entry["sha256"]:
            print(f"{name}: got {len(body)} bytes, sha256 {digest}; manifest differs")
            failed += 1
            continue
        (FOLDER / name).write_bytes(body)
        print(f"{name}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
