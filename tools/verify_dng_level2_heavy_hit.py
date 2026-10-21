#!/usr/bin/env python3
"""Verify two ordinary monster hits and their bounds on dungeon level two."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_startup import cpu_pc
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-level2-to3/action-004/key/handoff.json"
COMBAT = TRACE / "dng-level2-heavy-hit/handoff.json"
NEXT = TRACE / "dng-level2-to3/action-004/poll/handoff.json"
EVENT_PCS = ("0x9A0A", "0x9A62", "0x9A72", "0x9A95", "0x9AAC",
             "0x9B0C", "0x9B1A", "0x9A0A", "0x9A62", "0x9A72",
             "0x9A95", "0x9AAC", "0x9B0C", "0x9B1A", "0x8DDA")


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"level-two combat snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, COMBAT, NEXT)):
        print("PENDING DNG level-two two-hit replay")
        return 0
    source, combat, next_poll = [json.loads(path.read_text())
                                 for path in (SOURCE, COMBAT, NEXT)]
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]} and
            combat["timeout"] is None and
            combat["source_snapshot"] == next_poll["source_snapshot"] == source["snapshot"] and
            combat["working_game_disk"] == next_poll["working_game_disk"] == disk and
            cpu_pc(combat["final_cpu"]) == cpu_pc(next_poll["final_cpu"]) == 0x8DDA,
            "level-two combat ancestry differs")
    before = checked_ram(source["snapshot"])
    after = checked_ram(combat["snapshot"])
    alternate = checked_ram(next_poll["snapshot"])
    require(after == alternate and before[0xA506] == 2 and before[0xA60F] == 4 and
            before[0x7EC6:0x7EC8] == b"\x7e\x00" and
            after[0x7EC6:0x7EC8] == b"\x6e\x00" and
            combat["before_hp"] == "7e00" and combat["after_hp"] == "6e00",
            "level-two HP or independent RAM replay differs")
    events = combat["events"]
    require(tuple(event["pc"] for event in events) == EVENT_PCS and
            all(event["depth"] == "02" and event["threshold"] == "45"
                for event in events) and
            [event["actor_index"] for event in events[:7]] == ["05"] * 7 and
            [event["actor_index"] for event in events[7:14]] == ["01"] * 7 and
            " a=B6 " in events[1]["cpu"] and
            " a=4C " in events[8]["cpu"] and
            events[4]["damage"] == "1600" and
            events[11]["damage"] == "0600" and
            events[5]["roll"] == "0b00" and events[5]["damage"] == "0c00" and
            events[12]["roll"] == "0300" and events[12]["damage"] == "0400" and
            [events[i]["hp"] for i in (0, 5, 6, 7, 12, 13, 14)] ==
            ["7e00", "7e00", "7200", "7200", "7200", "6e00", "6e00"] and
            2 + before[0xA60F] * 5 == 22 and
            2 + before[0xA60F] * 1 == 6,
            "level-two hit rolls, bounds, damage, or HP stores differ")
    print("DNG level-two actor slots 5 and 1 hit: rolls $B6/$4C ≥ threshold $45")
    print("bounds 2+4×5=22 and 2+4×1=6; draws 11/3 → damage 12/4; HP 126→114→110")
    print("independent combat replay RAM matches the ordinary next-poll snapshot")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG level-two combat verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
