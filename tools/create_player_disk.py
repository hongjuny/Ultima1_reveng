#!/usr/bin/env python3
"""Create an ignored, disposable ProDOS player disk for GEN save tracing."""

import json
from pathlib import Path
import subprocess
import sys

from baseline import MANIFEST
from disassemble import ROOT


OUTPUT = ROOT / "build" / "baseline" / "U1PLAYER.po"
VOLUME = b"U1.PLAYER"


def main() -> int:
    cp2 = Path(json.loads(MANIFEST.read_text())["extractor"]["path"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to replace existing player disk: {OUTPUT}")
    subprocess.run([str(cp2), "create-disk-image", str(OUTPUT), "140k", "prodos"],
                   check=True)
    data = bytearray(OUTPUT.read_bytes())
    if len(data) != 143360 or data[1024 + 4] != 0xF7 or \
            data[1024 + 5:1024 + 12] != b"NEWDISK":
        raise RuntimeError("unexpected CiderPress ProDOS volume header")
    data[1024 + 4] = 0xF0 | len(VOLUME)
    data[1024 + 5:1024 + 20] = VOLUME.ljust(15, b"\x00")
    OUTPUT.write_bytes(data)
    result = subprocess.run([str(cp2), "catalog", str(OUTPUT)],
                            capture_output=True, text=True, check=True)
    if 'ProDOS "U1.PLAYER"' not in result.stdout:
        raise RuntimeError(f"player disk volume verification failed: {result.stdout}")
    print(f"private player disk: {OUTPUT}")
    print('verified ProDOS volume "U1.PLAYER" (140KB)')
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"player disk creation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
