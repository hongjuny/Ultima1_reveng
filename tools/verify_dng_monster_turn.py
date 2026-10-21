#!/usr/bin/env python3
"""Check the first ordinary dungeon monster HP loss and map movement."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-east-to-03-step-1/handoff.json"
MONSTER = TRACE / "dng-monster-turn/handoff.json"
ALTERNATE = TRACE / "dng-east-to-03-after-1/handoff.json"
NEXT = TRACE / "dng-east-to-03-step-2/handoff.json"
NEXT_POLL = TRACE / "dng-east-to-03-after-2/handoff.json"


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG monster snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, MONSTER, ALTERNATE,
                                           NEXT, NEXT_POLL)):
        print("PENDING DNG monster-turn replay")
        return 0
    source, monster, alternate, next_move, next_poll = [
        json.loads(path.read_text()) for path in
        (SOURCE, MONSTER, ALTERNATE, NEXT, NEXT_POLL)]
    require(all(item["timeout"] is None for item in
                (source, monster, alternate, next_move, next_poll)) and
            monster["source_snapshot"] == alternate["source_snapshot"] ==
            source["snapshot"] and
            next_move["source_snapshot"] == alternate["snapshot"] and
            next_poll["source_snapshot"] == next_move["snapshot"] and
            all(item["working_game_disk"] == source["working_game_disk"]
                for item in (monster, alternate, next_move, next_poll)),
            "DNG monster snapshot ancestry differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG monster game disk differs")
    before = checked_ram(source["snapshot"])
    after = checked_ram(monster["snapshot"])
    require(after == checked_ram(alternate["snapshot"]),
            "DNG monster replay does not match independent next poll")
    require([point["pc"] for point in monster["checkpoints"]] ==
            ["0x98EC", "0x9A0A", "0x9A5F", "0x9A62", "0x9A72", "0x9A95",
             "0x9AAC", "0x9ABD", "0x9B0C", "0x9B1A", "0x8DE6", "0x8DDA"] and
            [item["hp_7EC6_7EC7"] for item in monster["watched"]] ==
            ["9600"] * 9 + ["9400"] * 3 and
            before[0x7ECC] == 10 and before[0x7E7B] == 1 and
            before[0xA506] == before[0xA60D + before[0xA506]] ==
            before[0xA4FE] == 1 and
            ((before[0x7ECC] >> 1) + 8 * before[0x7E7B] + 0x38) & 0xFF == 0x45 and
            " a=A6 " in monster["checkpoints"][2]["cpu"] and
            monster["watched"][2]["threshold_a4fc"] == "45" and
            monster["watched"][6]["damage_a4f2_a4f3"] == "0200" and
            monster["watched"][7]["roll_a4f0_a4f1"] == "5300" and
            monster["watched"][8]["damage_a4f2_a4f3"] == "0200" and
            monster["watched"][8]["roll_a4f0_a4f1"] == "0100" and
            " a=94 " in monster["checkpoints"][8]["cpu"] and
            before[0x7EC6:0x7EC8] == b"\x96\x00" and
            after[0x7EC6:0x7EC8] == b"\x94\x00",
            "DNG monster damage path or amount differs")
    map_before, map_after = before[0xB099:0xB112], after[0xB099:0xB112]
    require([(i % 11, i // 11, a, b) for i, (a, b) in
             enumerate(zip(map_before, map_after)) if a != b] ==
            [(3, 3, 0, 0x30), (4, 3, 0x33, 3)],
            "DNG monster map changes differ")
    next_ram, next_poll_ram = checked_ram(next_move["snapshot"]), checked_ram(next_poll["snapshot"])
    require(" a=13 " in next_move["checkpoints"][5]["cpu"] and
            next_move["checkpoints"][6]["pc"] == "0x8EA7" and
            next_move["state_before"]["position"] ==
            next_move["state_after"]["position"] == "0301" and
            next_ram[0x7EC6:0x7EC8] == b"\x94\x00" and
            next_poll_ram[0x7EC6:0x7EC8] == b"\x92\x00",
            "DNG subsequent blocked input or HP differs")
    print("DNG hit: random $A6 ≥ threshold $45; damage bound $0002, first draw $53 rejected")
    print("DNG accepted damage $0002: HP $0096→$0094 at $9B0C")
    print("Two map cells changed during that turn; next blocked input reaches HP $0092")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG monster verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
