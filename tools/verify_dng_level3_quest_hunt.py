#!/usr/bin/env python3
"""Check a real level-three slot-5 kill after one accepted-quest intervention."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
HUNT = TRACE / "dng-level3-quest-hunt"


def report(path):
    value = json.loads(path.read_text())
    item = value["snapshot"]
    state = Path(item["path"])
    require(describe(state) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {state}")
    return value, main_ram(state)


def monster(ram):
    return (ram[0xA513], ram[0xA519],
            int.from_bytes(bytes((ram[0xA51F], ram[0xA525])), "little"))


def main():
    if not (HUNT / "route.json").is_file():
        print("PENDING level-three slot-5 quest hunt")
        return 0
    source, source_ram = report(TRACE / "dng-level3-entry/handoff.json")
    accepted, accepted_ram = report(HUNT / "accepted.json")
    require(accepted["source_snapshot"] == source["snapshot"] and
            accepted["working_game_disk"] == source["working_game_disk"] and
            accepted["intervention"] ==
            {"address": "0x7EAA", "before": 0, "after": 1},
            "quest hunt source differs")
    require([(index, left, right) for index, (left, right) in
             enumerate(zip(source_ram, accepted_ram)) if left != right] ==
            [(0x7EAA, 0, 1)],
            "accepted quest snapshot changed another RAM byte")
    route = json.loads((HUNT / "route.json").read_text())
    require([step["key"] for step in route] == [0x0A, 0x41, 0x41] and
            [step["quest_after"] for step in route] == [1, 1, 0xFF] and
            [step["completed"] for step in route] == [False, False, True],
            "quest hunt input sequence differs")
    states = [accepted_ram]
    preceding = accepted["snapshot"]
    for number, step in enumerate(route, 1):
        key, key_ram = report(HUNT / f"action-{number:03d}/key/handoff.json")
        require(key["source_snapshot"] == preceding and
                key["working_game_disk"] == source["working_game_disk"] and
                key["input"] == {"key_ascii": step["key"], "at_pc": "0x8DDA"} and
                key["timeout"] is None,
                f"quest hunt key {number} ancestry differs")
        if number < 3:
            following, next_ram = report(HUNT / f"action-{number:03d}/poll/handoff.json")
            require(following["source_snapshot"] == key["snapshot"] and
                    following["timeout"] is None and
                    following["final_cpu"].startswith("pc=8DDA "),
                    f"quest hunt poll {number} ancestry differs")
            states.append(next_ram)
            preceding = following["snapshot"]
        else:
            require(key["final_cpu"].startswith("pc=8E0E "),
                    "lethal attack did not return to dungeon handler")
            states.append(key_ram)
    require([ram[0xA506] for ram in states] == [3] * 4 and
            [tuple(ram[0xA4E8:0xA4EA]) for ram in states] == [(7, 3)] * 4 and
            [int.from_bytes(ram[0x7EC6:0x7EC8], "little") for ram in states] ==
            [108] * 4 and
            [monster(ram) for ram in states] ==
            [(7, 5, 30), (7, 4, 30), (7, 4, 2), (9, 7, 40)] and
            [ram[0x7EAA] for ram in states] == [1, 1, 1, 0xFF] and
            [ram[0xB099 + 4 * 11 + 7] for ram in states] ==
            [0x04, 0x54, 0x54, 0x04] and
            states[-1][0xB099 + 7 * 11 + 9] == 0x50,
            "level-three monster kill or odd quest result differs")
    print("DNG depth 3: one quest flag, Down/A/A killed actual slot 5; quest 1→$FF")
    print("Slot 5 HP 30→2→respawn 40; old map cell $54→$04; player HP 108")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"level-three quest hunt verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
