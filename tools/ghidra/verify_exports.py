#!/usr/bin/env python3
"""Check the local Ghidra call export against the public atlas's measured totals."""

from collections import Counter
import csv
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "build/ghidra-project"
sys.path.insert(0, str(ROOT / "tools"))
from disassemble import FILES
from build_command_matrix import KEY_ADDRESS, KEYS, TABLES
from build_code_data_ledger import verified_sets

EXPECTED = {
    "U1.SYSTEM": (3, 8), "U1.INTRO": (28, 32), "MAKE.INDATA": (6, 6),
    "MI.U1": (38, 76), "STUPH": (78, 42), "GEN": (19, 74),
    "OUT": (54, 126), "CAS": (43, 117), "TWN": (39, 99),
    "DNG": (63, 152), "SPA": (36, 101), "TM": (61, 136),
}
REVIEWED_EDGES = {
    "MI.U1": {(0x8907, 0xB703), (0x88F8, 0x8870)},
    "OUT": {(0x89A1, 0x836E), (0x8A6C, 0x15C5), (0x89CB, 0x82A2)},
    "CAS": {(0x89EE, 0x836E), (0x8A27, 0x15C2), (0x8A1F, 0x82A2)},
    "TWN": {(0x89EC, 0x836E), (0x8A1E, 0x15C2), (0x8A16, 0x82A2)},
    "SPA": {(0x8A5F, 0x15C2), (0x8A67, 0x82A2),
            (0x8FE8, 0xA154), (0x903A, 0xA154),
            (0x9068, 0xA154), (0x908E, 0xA154)},
    "TM": {(0x8E6A, 0x836E), (0x8E8E, 0x82A2)},
}


def main():
    totals = Counter()
    verified_code_count = 0
    verified_data_count = 0
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
        memory_path = EXPORTS / f"{name}-memory.tsv"
        with memory_path.open(newline="") as source:
            memory_rows = list(csv.DictReader(source, delimiter="\t"))
        spans = [(int(row["from"], 16), int(row["to"], 16) + 1,
                  row["operand"]) for row in memory_rows if row["kind"] == "span"]
        total_bytes = sum(end - start for start, end, _ in spans)
        if total_bytes != FILES[name][1]:
            raise ValueError(f"{name}: memory spans cover {total_bytes} bytes")
        if name == "MI.U1":
            data_addresses = {address for start, end, kind in spans
                              if kind == "defined_data" for address in range(start, end)}
            if not set(range(KEY_ADDRESS, KEY_ADDRESS + len(KEYS))) <= data_addresses:
                raise ValueError("MI.U1: shared key table was not typed as data")
        if name in TABLES:
            table_address, _ = TABLES[name]
            source = (ROOT / "extracted" / name).read_bytes()
            offset = table_address - FILES[name][0]
            expected_pointers = [(table_address + 2*i,
                                  int.from_bytes(source[offset + 2*i:offset + 2*i + 2], "little"))
                                 for i in range(len(KEYS))]
            actual_pointers = [(int(row["from"], 16), int(row["to"], 16))
                               for row in memory_rows if row["kind"] == "pointer"]
            if actual_pointers != expected_pointers:
                raise ValueError(f"{name}: Ghidra handler pointers differ from extracted bytes")
        code, data = verified_sets(name, *FILES[name][:2])
        instruction = {address for start, end, kind in spans
                       if kind == "instruction" for address in range(start, end)}
        defined = {address for start, end, kind in spans
                   if kind == "defined_data" for address in range(start, end)}
        if code - instruction:
            raise ValueError(f"{name}: Ghidra missed verified code at ${min(code-instruction):04X}")
        if data - defined:
            raise ValueError(f"{name}: Ghidra missed verified data at ${min(data-defined):04X}")
        if name in TABLES:
            local_targets = {target for _, target in expected_pointers
                             if FILES[name][0] <= target < FILES[name][0] + FILES[name][1]}
            if local_targets - instruction:
                raise ValueError(f"{name}: indirect handler target not decoded as code")
        verified_code_count += len(code)
        verified_data_count += len(data)
        print(f"{name}: {actual[0]} functions, {actual[1]} calls, "
              f"{len(code)} verified code and {len(data)} verified data bytes recognized")
    if (totals["function"], totals["call"]) != (468, 969):
        raise ValueError(f"aggregate changed: {totals}")
    if (verified_code_count, verified_data_count) != (3980, 406):
        raise ValueError("verified code/data byte counts changed")
    print("12 phase-separated programs; 468 function candidates, 969 direct calls, "
          "3980 verified code and 406 verified data bytes recognized")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
