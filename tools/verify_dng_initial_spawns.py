#!/usr/bin/env python3
"""Check first-floor actor initialization and map placement checkpoints."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "out-to-dng/handoff.json"
SPAWNS = TRACE / "dng-initial-spawns/handoff.json"
GENERATION = TRACE / "dng-generation/handoff.json"


def checked_ram(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG spawn snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, SPAWNS, GENERATION)):
        print("PENDING DNG initial actor spawns")
        return 0
    source, spawns, generation = [json.loads(path.read_text()) for path in
                                  (SOURCE, SPAWNS, GENERATION)]
    require(all(item["timeout"] is None for item in
                (source, spawns, generation)) and
            spawns["source_snapshot"] == generation["source_snapshot"] ==
            source["snapshot"] and
            spawns["working_game_disk"] == generation["working_game_disk"] ==
            source["working_game_disk"], "DNG spawn ancestry differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG spawn game disk differs")
    final_ram = checked_ram(spawns["snapshot"])
    require(final_ram == checked_ram(generation["snapshot"]),
            "DNG initial spawn replay differs from generator return")
    points = spawns["checkpoints"]
    require([item["pc"] for item in points] ==
            ["0x9BED", "0x9C11"] +
            [pc for _ in range(3) for pc in
             ("0x9C82", "0x9C8F", "0x9C92")] +
            ["0x8DE6"], "DNG spawn checkpoints differ")
    require(points[1]["active_flags"] == "0101010101" and
            points[1]["remaining"] == 3 and
            points[1]["type_base"] == "14" and
            [(points[i]["slot"], points[i]["x"], points[i]["y"],
              points[i]["remaining"], points[i]["active_flags"])
             for i in (2, 5, 8)] ==
            [(3, 5, 3, 3, "0101000101"),
             (1, 5, 1, 2, "0001000101"),
             (2, 7, 9, 1, "0000000101")],
            "DNG selected actor slots or positions differ")
    previous = bytes.fromhex(points[1]["map_hex"])
    for item_index in (2, 5, 8):
        accepted, ready, written = points[item_index:item_index + 3]
        slot, x, y = accepted["slot"], accepted["x"], accepted["y"]
        offset = y * 11 + x
        require(accepted["cell"] == ready["cell"] == 0 and
                written["cell"] == slot << 4 and
                bytes.fromhex(accepted["map_hex"]) ==
                bytes.fromhex(ready["map_hex"]) == previous,
                "DNG spawn pre-write map differs")
        expected = bytearray(previous)
        expected[offset] = slot << 4
        previous = bytes(expected)
        require(bytes.fromhex(written["map_hex"]) == previous,
                "DNG spawn changed unexpected map cells")
    require(bytes.fromhex(points[-1]["map_hex"]) == previous and
            points[-1]["remaining"] == 0 and
            points[-1]["active_flags"] == "0000000101" and
            points[-1]["actor_hp"] == "000b0c0d0000" and
            final_ram[0xA506] == 1 and final_ram[0xA60E] == 1 and
            final_ram[0xA51A:0xA520] == bytes((0, 11, 12, 13, 0, 0)) and
            final_ram[0xA520:0xA526] == bytes(6) and
            [points[i]["actor_hp"] for i in (2, 5, 8)] ==
            ["0000000d0000", "000b000d0000", "000b0c0d0000"],
            "DNG final actor state differs")
    print("DNG first-floor spawn order: slot 3 at (5,3), 1 at (5,1), 2 at (7,9)")
    print("Flags 1→0 mark active slots; only three map cells change; full RAM matches generator replay")
    print("First-floor actor HP: 10 + $A60E×slot = 13, 11, 12 in spawn order")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG initial spawn verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
