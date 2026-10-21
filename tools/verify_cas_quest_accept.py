#!/usr/bin/env python3
"""Check controlled T/S acceptance at the first castle king tile."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
REPORT = TRACE / "cas-quest-accept/handoff.json"


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not REPORT.is_file():
        print("PENDING controlled CAS king quest acceptance")
        return 0
    source = json.loads((TRACE / "cas-first-input/handoff.json").read_text())
    trial = json.loads(REPORT.read_text())
    require(trial["source_snapshot"] == source["snapshot"] and
            trial["working_game_disk"] == source["working_game_disk"],
            "castle quest trace ancestry differs")
    before, after = checked(source["snapshot"]), checked(trial["snapshot"])
    require(trial["intervention"] ==
            {"address": "0x0000", "before": [0, 9], "after": [31, 6]} and
            list(before[:2]) == [0, 9] and
            before[0xB400 + 6 * 38 + 31] == 0x6C and
            trial["inputs"] == [84, 83],
            "king tile or input intervention differs")
    require(trial["before"] == {"position": [0, 9], "quest": [0] * 8,
                                "world_location": 0, "group": 0,
                                "castle_index": 6} and
            trial["after_quest"] == [0, 0, 0, 0, 0, 0, 1, 0] and
            list(after[0x7EA9:0x7EB1]) == trial["after_quest"],
            "castle quest byte differs")
    require([point["pc"] for point in trial["checkpoints"]] ==
            ["0x927C", "0x92AA", "0x92CC", "0x8A25", "0x93FB", "0x9437", "0x943A"] and
            " a=6C " in trial["checkpoints"][1]["cpu"] and
            " a=53 " in trial["checkpoints"][4]["cpu"] and
            " x=06 " in trial["checkpoints"][5]["cpu"],
            "castle king path differs")
    print("CAS king tile $6C: T, S accepted even quest 6; $7EAF 0→1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"castle quest verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
