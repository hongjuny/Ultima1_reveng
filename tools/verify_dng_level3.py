#!/usr/bin/env python3
"""Verify the ordinary second-floor route and level-three handoff."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_startup import cpu_pc
from verify_dng_stairs import checked_ram, facing, position, tile
from verify_intro_support import require


TRACE = ROOT / "build/traces"
START = TRACE / "dng-stairs-k/handoff.json"
ROUTE = TRACE / "dng-level2-to3/route.json"
ENTRY = TRACE / "dng-level3-entry/handoff.json"
EXPECTED_KEYS = (10, 11, 11, 21, 11, 11, 11, 11, 8, 11, 11)
EXPECTED_HP = (130, 130, 126, 110, 110, 110, 110, 110, 108, 108, 108)


def main() -> int:
    if not all(path.is_file() for path in (START, ROUTE, ENTRY)):
        print("PENDING DNG level-two route to level three")
        return 0
    start = json.loads(START.read_text())
    actions = json.loads(ROUTE.read_text())
    entry = json.loads(ENTRY.read_text())
    require(len(actions) == len(EXPECTED_KEYS) and
            tuple(item["key"] for item in actions) == EXPECTED_KEYS and
            tuple(item["hp_after"] for item in actions) == EXPECTED_HP,
            "level-two route input or HP sequence differs")
    disk = start["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "level-two game disk differs")
    source = start
    ram = checked_ram(source["snapshot"])
    start_map = ram[0xB099:0xB112]
    require(position(ram) == (3, 7) and facing(ram) == (0, 1) and
            ram[0xA506] == 2 and tile(ram) == 8 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 131 and
            [i for i, value in enumerate(start_map) if value == 7] == [40],
            "first level-two input or $07 stair differs")
    for index, action in enumerate(actions, 1):
        key_path = TRACE / f"dng-level2-to3/action-{index:03d}/key/handoff.json"
        poll_path = TRACE / f"dng-level2-to3/action-{index:03d}/poll/handoff.json"
        require(Path(action["key_report"]).resolve() == key_path.resolve() and
                Path(action["poll_report"]).resolve() == poll_path.resolve(),
                f"level-two action {index} report path differs")
        key_report = json.loads(key_path.read_text())
        poll_report = json.loads(poll_path.read_text())
        require(key_report["timeout"] is None and poll_report["timeout"] is None and
                key_report["source_snapshot"] == source["snapshot"] and
                poll_report["source_snapshot"] == key_report["snapshot"] and
                key_report["working_game_disk"] == poll_report["working_game_disk"] == disk and
                key_report["input"] == {"key_ascii": action["key"], "at_pc": "0x8DDA"} and
                cpu_pc(poll_report["final_cpu"]) == 0x8DDA,
                f"level-two action {index} ancestry or input differs")
        before = checked_ram(key_report["source_snapshot"])
        key_ram = checked_ram(key_report["snapshot"])
        after = checked_ram(poll_report["snapshot"])
        require(before == ram and
                list(position(before)) == action["before"] and
                list(facing(before)) == action["facing_before"] and
                tile(before) == action["tile_before"] and
                before[0xA506] == action["depth_before"] == 2 and
                int.from_bytes(before[0x7EC6:0x7EC8], "little") == action["hp_before"] and
                list(position(after)) == action["after"] and
                list(facing(after)) == action["facing_after"] and
                tile(after) == action["tile_after"] and
                after[0xA506] == action["depth_after"] == 2 and
                int.from_bytes(after[0x7EC6:0x7EC8], "little") == action["hp_after"] and
                position(key_ram) == position(after) and facing(key_ram) == facing(after),
                f"level-two action {index} state differs")
        ram, source = after, poll_report
    require(position(ram) == (7, 3) and facing(ram) == (0, -1) and
            tile(ram) == 7 and int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 108,
            "level-two descending stair arrival differs")
    third = checked_ram(entry["snapshot"])
    require(entry["timeout"] is None and
            entry["source_snapshot"] == source["snapshot"] and
            entry["working_game_disk"] == disk and
            entry["input"] == {"key_ascii": 75, "at_pc": "0x8DDA"} and
            entry["before"] == {"position": "0703", "facing": "00ff", "depth": "02",
                                "tile": "07", "hp": "6c00", "food": "b400"} and
            [point["pc"] for point in entry["checkpoints"]] ==
            ["0x8DE4", "0x8DD7", "0x8E0B", "0x961B", "0x963F", "0x9666",
             "0x972C", "0x8C5D", "0x8DDA"] and
            entry["after"] == {"position": "0703", "facing": "00ff", "depth": "03",
                               "tile": "08", "hp": "6c00", "food": "b400"} and
            position(third) == (7, 3) and facing(third) == (0, -1) and
            third[0xA506] == 3 and tile(third) == 8 and
            int.from_bytes(third[0x7EC6:0x7EC8], "little") == 108 and
            third[0xB099:0xB112] != start_map and
            cpu_pc(entry["final_cpu"]) == 0x8DDA,
            "level-three entry differs")
    print("DNG level 2: 11 direction keys (3,7)→(7,3); HP 131→108")
    print("K facing north on $07: $963F→$9666→$972C→$8C5D; depth 2→3, tile $07→$08")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG level-three verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
