#!/usr/bin/env python3
"""Check map high nibbles against live dungeon actor-slot coordinates."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SAMPLES = (
    "dng-first-input", "dng-descend/stairs-turn/poll", "dng-stairs-k",
    "dng-level2-ascend", "dng-level3-entry",
    *(f"dng-level2-to3/action-{index:03d}/poll" for index in range(1, 12)),
)


def main() -> int:
    paths = [TRACE / name / "handoff.json" for name in SAMPLES]
    if not all(path.is_file() for path in paths):
        print("PENDING dungeon actor-map snapshots")
        return 0
    observed = 0
    for name, path in zip(SAMPLES, paths):
        report = json.loads(path.read_text())
        item = report["snapshot"]
        snapshot = Path(item["path"])
        require(describe(snapshot) == {"size": item["size"], "sha256": item["sha256"]},
                f"{name}: snapshot differs")
        ram = main_ram(snapshot)
        grid = ram[0xB099:0xB112]
        occupied = [(index, value >> 4) for index, value in enumerate(grid)
                    if value >> 4]
        require(len(occupied) == 3,
                f"{name}: observed active actor count differs")
        slots = set()
        for index, slot in occupied:
            x, y = index % 11, index // 11
            require(1 <= slot <= 5 and slot not in slots and
                    ram[0xA50E + slot] == x and ram[0xA514 + slot] == y and
                    ram[0xA508 + slot] == 0,
                    f"{name}: map actor slot {slot} at ({x},{y}) differs")
            slots.add(slot)
            observed += 1
    print(f"DNG actor map: {observed} occupied cells across {len(SAMPLES)} snapshots")
    print("high nibble = active slot 1–5; $A50E[slot]/$A514[slot] match its (x,y)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG actor-map verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
