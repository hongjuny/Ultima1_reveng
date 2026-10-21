#!/usr/bin/env python3
"""Verify the four 80-slot outdoor-object arrays in the saved player record."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
START, END = 0x7E6D, 0x8037
COUNT = 0x7EF6
X, Y, TILE, UNDER = 0x7EF7, 0x7F47, 0x7F97, 0x7FE7
CAPACITY = 0x50


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not (TRACE / "final-craft-spawn/handoff.json").is_file():
        print("PENDING controlled outdoor-object record")
        return 0
    ordinary = json.loads((TRACE / "cas-to-out/handoff.json").read_text())
    created = json.loads((TRACE / "final-craft-spawn/handoff.json").read_text())
    source = json.loads((TRACE / "cas-exit-left/handoff.json").read_text())
    require(ordinary["source_snapshot"] == created["source_snapshot"] ==
            source["snapshot"] and
            ordinary["working_game_disk"] == created["working_game_disk"] and
            created["intervention"] ==
            {"address": "0x7EB5", "before": 0, "after": 1},
            "object replay ancestry or single-byte intervention differs")
    before, after = checked(ordinary["snapshot"]), checked(created["snapshot"])
    require(END - START == 458 and X == COUNT + 1 and
            Y == X + CAPACITY and TILE == Y + CAPACITY and
            UNDER == TILE + CAPACITY and END == UNDER + CAPACITY,
            "player record array boundaries differ")
    changes = [(address, before[address], after[address])
               for address in range(START, END)
               if before[address] != after[address]]
    require(changes == [(COUNT, 0, 1), (X, 0, 6), (Y, 0, 7),
                        (TILE, 0, 0x1E), (UNDER, 0, 4)],
            f"controlled creation changed unexpected record bytes: {changes}")
    require(created["placement"] ==
            {"x": 6, "y": 7, "address": 0x61C6, "raw_before": 4,
             "raw_after": 0x1E, "raw_at_poll": 0x1E,
             "request_after": 0, "objects_after": 1} and
            before[0x61C6] == 4 and after[0x61C6] == 0x1E,
            "record slot does not match the changed map cell")
    code = (ROOT / "extracted/OUT").read_bytes()
    at = lambda address, length: code[address - 0x8956:address - 0x8956 + length]
    require(at(0x9931, 6) == bytes.fromhex("aef67ee050b0"),
            "object writer does not guard the 80-slot count")
    print("U1.VARS: $7EF6 count + four 80-byte arrays $7EF7–$8036")
    print("Controlled spawn changed only count and slot zero: x=6 y=7 tile=$1E beneath=$04")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"player object record verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
