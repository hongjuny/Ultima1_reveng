#!/usr/bin/env python3
"""Verify the private ordinary-play route to the first descending stairs."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_startup import cpu_pc
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
INITIAL = TRACE / "dng-first-input/handoff.json"
ROUTE = TRACE / "dng-descend/route.json"
TURN_KEY = TRACE / "dng-descend/stairs-turn/key/handoff.json"
TURN_POLL = TRACE / "dng-descend/stairs-turn/poll/handoff.json"
STAIRS = TRACE / "dng-stairs-k/handoff.json"
ASCENT = TRACE / "dng-level2-ascend/handoff.json"
EXPECTED_KEYS = (11, 11, 8, 11, 11, 21, 11, 11, 21, 11, 11, 8, 11, 11, 8, 11, 11)


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"dungeon stair snapshot differs: {path}")
    return main_ram(path)


def position(ram: bytes) -> tuple[int, int]:
    return tuple(ram[0xA4E8:0xA4EA])


def facing(ram: bytes) -> tuple[int, int]:
    return tuple(v - 256 if v >= 128 else v for v in ram[0xA4EC:0xA4EE])


def tile(ram: bytes) -> int:
    x, y = position(ram)
    return ram[0xB099 + 11*y + x]


def main() -> int:
    paths = (INITIAL, ROUTE, TURN_KEY, TURN_POLL, STAIRS, ASCENT)
    if not all(path.is_file() for path in paths):
        print("PENDING DNG route and two-way stair replay")
        return 0
    initial = json.loads(INITIAL.read_text())
    actions = json.loads(ROUTE.read_text())
    require(len(actions) == len(EXPECTED_KEYS) and
            tuple(action["key"] for action in actions) == EXPECTED_KEYS,
            "first dungeon stair route differs")
    disk = initial["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "dungeon stair game disk differs")
    source = initial
    ram = checked_ram(source["snapshot"])
    require(position(ram) == (1, 1) and facing(ram) == (0, 1) and
            ram[0xA506] == 1 and tile(ram) == 8,
            "first dungeon poll differs")
    for index, action in enumerate(actions, 1):
        key_path = TRACE / f"dng-descend/action-{index:03d}/key/handoff.json"
        poll_path = TRACE / f"dng-descend/action-{index:03d}/poll/handoff.json"
        require(Path(action["key_report"]).resolve() == key_path.resolve() and
                Path(action["poll_report"]).resolve() == poll_path.resolve(),
                f"action {index} report path differs")
        key_report = json.loads(key_path.read_text())
        poll_report = json.loads(poll_path.read_text())
        require(key_report["timeout"] is None and poll_report["timeout"] is None and
                key_report["source_snapshot"] == source["snapshot"] and
                poll_report["source_snapshot"] == key_report["snapshot"] and
                key_report["working_game_disk"] == poll_report["working_game_disk"] == disk and
                key_report["input"] == {"key_ascii": action["key"], "at_pc": "0x8DDA"} and
                cpu_pc(poll_report["final_cpu"]) == 0x8DDA,
                f"action {index} ancestry or input differs")
        before = checked_ram(key_report["source_snapshot"])
        key_ram = checked_ram(key_report["snapshot"])
        after = checked_ram(poll_report["snapshot"])
        require(before == ram and
                list(position(before)) == action["before"] and
                list(facing(before)) == action["facing_before"] and
                tile(before) == action["tile_before"] and
                before[0xA506] == action["depth_before"] and
                int.from_bytes(before[0x7EC6:0x7EC8], "little") == action["hp_before"] and
                list(position(after)) == action["after"] and
                list(facing(after)) == action["facing_after"] and
                tile(after) == action["tile_after"] and
                after[0xA506] == action["depth_after"] == 1 and
                int.from_bytes(after[0x7EC6:0x7EC8], "little") == action["hp_after"] and
                position(key_ram) == position(after) and facing(key_ram) == facing(after),
                f"action {index} state differs")
        ram, source = after, poll_report
    require(position(ram) == (3, 7) and facing(ram) == (1, 0) and
            tile(ram) == 7 and int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 139,
            "descending stair arrival differs")
    turn_key, turn_poll, stairs = [json.loads(path.read_text())
                                   for path in (TURN_KEY, TURN_POLL, STAIRS)]
    require(turn_key["timeout"] is None and turn_poll["timeout"] is None and
            stairs["timeout"] is None and
            turn_key["source_snapshot"] == source["snapshot"] and
            turn_poll["source_snapshot"] == turn_key["snapshot"] and
            stairs["source_snapshot"] == turn_poll["snapshot"] and
            all(report["working_game_disk"] == disk for report in (turn_key, turn_poll, stairs)) and
            turn_key["input"] == {"key_ascii": 21, "at_pc": "0x8DDA"} and
            stairs["input"] == {"key_ascii": 75, "at_pc": "0x8DDA"},
            "stair turn or K ancestry differs")
    turn_ram = checked_ram(turn_poll["snapshot"])
    stairs_ram = checked_ram(stairs["snapshot"])
    require(position(turn_ram) == (3, 7) and facing(turn_ram) == (0, 1) and
            tile(turn_ram) == 7 and turn_ram[0xA506] == 1 and
            stairs["before"] == {"position": "0307", "facing": "0001", "depth": "01",
                                  "tile": "07", "hp": "8a00", "food": "b400"} and
            [point["pc"] for point in stairs["checkpoints"]] ==
            ["0x8DE4", "0x8DD7", "0x8E0B", "0x961B", "0x963F", "0x9666",
             "0x972C", "0x8C5D", "0x8DDA"] and
            stairs["after"] == {"position": "0307", "facing": "0001", "depth": "02",
                                 "tile": "08", "hp": "8300", "food": "b400"} and
            position(stairs_ram) == (3, 7) and facing(stairs_ram) == (0, 1) and
            stairs_ram[0xA506] == 2 and tile(stairs_ram) == 8 and
            cpu_pc(stairs["final_cpu"]) == 0x8DDA,
            "DNG level-two entry differs")
    ascent = json.loads(ASCENT.read_text())
    ascent_ram = checked_ram(ascent["snapshot"])
    require(ascent["timeout"] is None and
            ascent["source_snapshot"] == stairs["snapshot"] and
            ascent["working_game_disk"] == disk and
            ascent["input"] == {"key_ascii": 75, "at_pc": "0x8DDA"} and
            ascent["before"] == stairs["after"] and
            [point["pc"] for point in ascent["checkpoints"]] ==
            ["0x8DE4", "0x8DD7", "0x8E0B", "0x961B", "0x963F", "0x9666",
             "0x9670", "0x9728", "0x8C5D", "0x8DDA"] and
            ascent["after"] == {"position": "0307", "facing": "0001", "depth": "01",
                                 "tile": "07", "hp": "8300", "food": "b400"} and
            position(ascent_ram) == (3, 7) and facing(ascent_ram) == (0, 1) and
            ascent_ram[0xA506] == 1 and tile(ascent_ram) == 7 and
            cpu_pc(ascent["final_cpu"]) == 0x8DDA,
            "DNG level-one return differs")
    initial_map = checked_ram(initial["snapshot"])[0xB099:0xB112]
    return_map = ascent_ram[0xB099:0xB112]
    changed_base_tiles = [(i % 11, i // 11, initial_map[i] & 15, return_map[i] & 15)
                          for i in range(121) if (initial_map[i] & 15) != (return_map[i] & 15)]
    require(changed_base_tiles == [(2, 3, 5, 6)],
            "observed first-floor map change differs")
    print("DNG $07 route: 17 keys from (1,1) to (3,7); HP 150→139")
    print("K facing south: $963F→$9666→$972C→$8C5D; depth 1→2, tile $07→$08")
    print("K on level-two $08: $9670→$9728→$8C5D; depth 2→1, tile $08→$07")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG stair verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
