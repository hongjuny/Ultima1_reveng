#!/usr/bin/env python3
"""Check the local Ghidra call export against the public atlas's measured totals."""

from collections import Counter
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "build/ghidra-project"
EXPECTED = {
    "U1.SYSTEM": (3, 8), "U1.INTRO": (26, 32), "MAKE.INDATA": (6, 6),
    "MI.U1": (32, 69), "STUPH": (25, 24), "GEN": (7, 25),
    "OUT": (24, 58), "CAS": (13, 55), "TWN": (14, 46),
    "DNG": (18, 72), "SPA": (10, 40), "TM": (34, 78),
}
REVIEWED_EDGES = {
    "MI.U1": {(0x8907, 0xB703), (0x88F8, 0x8870)},
    "OUT": {(0x89A1, 0x836E), (0x8A6C, 0x15C5), (0x89CB, 0x82A2)},
    "CAS": {(0x89EE, 0x836E), (0x8A27, 0x15C2), (0x8A1F, 0x82A2)},
    "TWN": {(0x89EC, 0x836E), (0x8A1E, 0x15C2), (0x8A16, 0x82A2)},
    "SPA": {(0x8A5F, 0x15C2), (0x8A67, 0x82A2)},
    "TM": {(0x8E6A, 0x836E), (0x8E8E, 0x82A2)},
}


def main():
    totals = Counter()
    for name, expected in EXPECTED.items():
        path = EXPORTS / f"{name}-calls.tsv"
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open(newline="") as source:
            rows = list(csv.DictReader(source, delimiter="\t"))
        counts = Counter(row["kind"] for row in rows)
        actual = (counts["function"], counts["call"])
        if actual != expected or any(row["program"] != name for row in rows):
            raise ValueError(f"{name}: expected {expected}, got {actual}")
        edges = {(int(row["from"], 16), int(row["to"], 16))
                 for row in rows if row["kind"] == "call"}
        missing = REVIEWED_EDGES.get(name, set()) - edges
        if missing:
            raise ValueError(f"{name}: reviewed edges missing from candidate graph: {missing}")
        totals.update(counts)
        print(f"{name}: {actual[0]} candidate functions, {actual[1]} direct calls")
    if (totals["function"], totals["call"]) != (212, 513):
        raise ValueError(f"aggregate changed: {totals}")
    print("12 phase-separated Ghidra programs and reviewed cross-layer edges verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
