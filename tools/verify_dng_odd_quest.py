#!/usr/bin/env python3
"""Check the controlled odd quest completion branch after a real lethal attack."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
REPORT = TRACE / "dng-odd-quest/handoff.json"


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not REPORT.is_file():
        print("PENDING controlled DNG odd quest completion")
        return 0
    source = json.loads((TRACE / "dng-attack-repeat-3/poll/handoff.json").read_text())
    trial = json.loads(REPORT.read_text())
    require(trial["source_snapshot"] == source["snapshot"] and
            trial["working_game_disk"] == source["working_game_disk"],
            "DNG quest replay ancestry differs")
    prior, completed = checked(source["snapshot"]), checked(trial["snapshot"])
    require(trial["input"] == 65 and
            trial["before"] == {"type": 1, "depth": 1, "quest": [0] * 8} and
            trial["interventions"] ==
            [{"address": "0xA52E", "before": 1, "after": 5},
             {"address": "0xA506", "before": 1, "after": 3},
             {"address": "0x7EAA", "before": 0, "after": 1}] and
            prior[0xA506] == 1 and list(prior[0x7EA9:0x7EB1]) == [0] * 8,
            "DNG quest intervention differs")
    require([point["pc"] for point in trial["checkpoints"]] ==
            ["0x94A7", "0x94C3", "0x94C6"] and
            " x=01 " in trial["checkpoints"][1]["cpu"],
            "DNG quest write path differs")
    require(trial["after"] == {"type": 5, "depth": 3,
                               "quest": [0, 0xFF] + [0] * 6} and
            completed[0xA52E] == 5 and completed[0xA506] == 3 and
            list(completed[0x7EA9:0x7EB1]) == trial["after"]["quest"],
            "DNG odd quest completion differs")
    print("DNG lethal attack, controlled type 5/depth 3: accepted quest 1 became $FF")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG odd quest verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
