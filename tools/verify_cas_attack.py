#!/usr/bin/env python3
"""Verify castle attack targeting, hit, damage, and observed retaliation."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
TARGET = TRACE / "cas-attack-target" / "handoff.json"
EFFECT = TRACE / "cas-attack-effect" / "handoff.json"


def checked_snapshot(report: dict) -> bytearray:
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "castle attack snapshot differs")
    return main_ram(path)


def main() -> int:
    if not EFFECT.is_file():
        print("PENDING CAS attack trace")
        return 0
    source = json.loads((TRACE / "cas-occupied-tile" / "step-02" / "handoff.json").read_text())
    target = json.loads(TARGET.read_text())
    effect = json.loads(EFFECT.read_text())
    require(target["timeout"] is None and
            target["source_snapshot"] == source["snapshot"] and
            target["working_game_disk"] == source["working_game_disk"] and
            target["inputs"] == [65, 11],
            "attack target ancestry or inputs differ")
    require([point["pc"] for point in target["checkpoints"]] ==
            ["0x8A2F", "0x8A4A", "0x8A56", "0x8C56", "0x8A27",
             "0x8C82", "0x8CC9", "0x8D08"],
            "attack target path differs")
    require(target["before"] ==
            {"position": [1, 7], "actor_slot_2": [1, 6, 3], "tile_1_6": 0x60} and
            target["after"]["position"] == [1, 7] and
            target["after"]["candidate"] == [1, 6] and
            target["after"]["actor_index"] == 2 and
            " a=33 " in target["checkpoints"][-1]["cpu"],
            "attack did not target slot 2 on a passable tile")
    before = main_ram(Path(source["snapshot"]["path"]))
    target_ram = checked_snapshot(target)
    require(target_ram[0xB6DE:0xB6DF] == before[0xB6DE:0xB6DF] and
            target_ram[0xB6EE] == before[0xB6EE] and
            target_ram[0x7EC6:0x7EC8] == before[0x7EC6:0x7EC8],
            "health changed before attack resolution")
    require(effect["timeout"] is None and
            effect["source_snapshot"] == target["snapshot"] and
            effect["working_game_disk"] == target["working_game_disk"],
            "attack effect ancestry differs")
    require([point["pc"] for point in effect["checkpoints"]] ==
            ["0x8D27", "0x8D71", "0x8A59", "0x8A27"] and
            " a=85 " in effect["checkpoints"][0]["cpu"],
            "expected hit and actor-damage path differs")
    at_return = effect["watched_at_handler_return"]
    require(at_return["$B6DE"] == 0xDA and at_return["$B6EE"] == 0x01 and
            at_return["$7EC6"] == 0x96 and at_return["$9E2A"] == 1,
            "attack handler return state differs")
    after = checked_snapshot(effect)
    require((target_ram[0xB6DE], target_ram[0xB6EE],
             after[0xB6DE], after[0xB6EE]) == (0xF4, 0x01, 0xDA, 0x01),
            "actor HP did not fall by 26")
    require((target_ram[0x7EC6], target_ram[0x7EC7],
             after[0x7EC6], after[0x7EC7]) == (0x96, 0, 0x87, 0),
            "player HP did not fall by 15")
    require(after[0x9E2A] == 1 and
            after[0:2] == target_ram[0:2] == bytes((1, 7)) and
            after[0xB6AE] == 3 and after[0xB6BE] == 1 and after[0xB6CE] == 6 and
            after[0x7EE4] == target_ram[0x7EE4] == 0x42 and
            after[0x7EDA] == target_ram[0x7EDA] == 0x30 and
            after[0x7EE5:0x7EE7] == target_ram[0x7EE5:0x7EE7],
            "attack survivor or other watched state differs")
    require(effect["final_cpu"] == effect["checkpoints"][-1]["cpu"],
            "attack did not return to castle input")
    print("CAS A/Up: actor slot 2 at (1,6), hit roll $85 < $A3")
    print("actor HP $01F4→$01DA in handler; player HP $0096→$0087 after return")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS attack verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
