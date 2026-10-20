#!/usr/bin/env python3
"""Create local, unreviewed da65 listings from user-supplied extracted files.

Outputs include bytes from the original game and must remain outside Git.
"""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "U1.SYSTEM": (0x2000, 1682, "startup"),
    "U1.INTRO": (0x0800, 2469, "intro"),
    "MAKE.INDATA": (0x1E00, 13877, "intro support"),
    "MI.U1": (0x7000, 6589, "common engine"),
    "STUPH": (0x0800, 6144, "graphics and shared routines"),
    "GEN": (0x8956, 8932, "character generation"),
    "OUT": (0x8956, 5230, "outdoors"),
    "DNG": (0x8956, 10051, "dungeon"),
    "TWN": (0x8956, 8461, "town"),
    "CAS": (0x8956, 5524, "castle"),
    "SPA": (0x8956, 9930, "space"),
    "TM": (0x8956, 8123, "time machine / finale"),
    "MAPCHARS": (0x0800, 1024, "graphics data"),
    "TCMAPS": (0x4000, 7660, "map data"),
    "NIF": (0x4000, 7680, "data"),
    "PRODOS": (0x2000, 14848, "operating system"),
}
CODE_FILES = tuple(FILES)[:12]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate inputs only")
    parser.add_argument("--only", nargs="+", choices=CODE_FILES, help="select code files")
    args = parser.parse_args()
    source = ROOT / "extracted"
    missing_or_wrong = False
    for name, (address, expected, kind) in FILES.items():
        path = source / name
        if not path.is_file():
            print(f"MISSING {name}", file=sys.stderr)
            missing_or_wrong = True
            continue
        actual = path.stat().st_size
        if actual != expected:
            print(f"SIZE MISMATCH {name}: expected {expected}, got {actual}", file=sys.stderr)
            missing_or_wrong = True
        else:
            print(f"{name:12} ${address:04X}-${address+actual-1:04X} {kind}")
    if missing_or_wrong:
        return 1
    if args.check:
        return 0
    executable = shutil.which("da65")
    if not executable:
        parser.error("da65 is required (install cc65)")
    output = ROOT / "build" / "disassembly"
    output.mkdir(parents=True, exist_ok=True)
    for name in args.only or CODE_FILES:
        address = FILES[name][0]
        target = output / f"{name}.s"
        subprocess.run(
            [executable, "--cpu", "6502", "-S", f"0x{address:04x}",
             "-o", str(target), str(source / name)],
            check=True,
        )
        print(f"wrote {target.relative_to(ROOT)} (unreviewed; do not publish)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
