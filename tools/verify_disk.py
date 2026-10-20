#!/usr/bin/env python3
"""Re-extract the private disk image and compare all files with extracted/."""

import filecmp
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from disassemble import FILES, ROOT


MANIFEST = ROOT / "build" / "baseline" / "manifest.json"


def main() -> int:
    if not MANIFEST.is_file():
        print("no local baseline", file=sys.stderr)
        return 2
    baseline = json.loads(MANIFEST.read_text())
    if not baseline.get("disk_image") or not baseline.get("extractor"):
        print("baseline needs a disk image and extractor", file=sys.stderr)
        return 2
    disk = Path(baseline["disk_image"]["path"])
    extractor = Path(baseline["extractor"]["path"])
    with tempfile.TemporaryDirectory(prefix="u1-disk-compare-") as temporary:
        destination = Path(temporary)
        result = subprocess.run(
            [str(extractor), "extract", str(disk)],
            cwd=destination, capture_output=True, text=True,
        )
        if result.returncode:
            print(result.stderr or result.stdout, file=sys.stderr)
            return result.returncode
        found = {path.name for path in destination.iterdir() if path.is_file()}
        if found != set(FILES):
            print(f"disk file list differs: missing={sorted(set(FILES)-found)}, "
                  f"extra={sorted(found-set(FILES))}", file=sys.stderr)
            return 1
        mismatches = [
            name for name in FILES
            if not filecmp.cmp(destination / name, ROOT / "extracted" / name, shallow=False)
        ]
        if mismatches:
            print(f"extracted files differ from disk: {', '.join(mismatches)}", file=sys.stderr)
            return 1
    print(f"all {len(FILES)} extracted files match a fresh CiderPress extraction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
