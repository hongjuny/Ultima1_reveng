#!/usr/bin/env python3
"""List and validate the resident STUPH jump interface without exporting data."""

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = 0x0800
FIRST = 0x1583
AFTER_LAST = 0x15E9


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="print only a summary")
    args = parser.parse_args()
    data = (ROOT / "extracted" / "STUPH").read_bytes()
    if len(data) != 0x1800:
        raise SystemExit(f"STUPH: expected 6144 bytes, got {len(data)}")
    vectors = []
    for address in range(FIRST, AFTER_LAST, 3):
        offset = address - BASE
        if data[offset] != 0x4C:
            raise SystemExit(f"STUPH: ${address:04X} is not JMP absolute")
        target = data[offset + 1] | (data[offset + 2] << 8)
        if not 0x1580 <= target < 0x2000:
            raise SystemExit(f"STUPH: ${address:04X} target ${target:04X} is outside support code")
        vectors.append((address, target))
    if len(vectors) != 34:
        raise SystemExit(f"STUPH: expected 34 vectors, got {len(vectors)}")
    if not args.check:
        for address, target in vectors:
            print(f"${address:04X} -> ${target:04X}")
    print(f"validated {len(vectors)} STUPH jump vectors at $1583-$15E8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
