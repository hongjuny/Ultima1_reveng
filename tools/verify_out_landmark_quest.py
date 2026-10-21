#!/usr/bin/env python3
"""Check controlled completion of an even castle quest at a real map landmark."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
REPORT = TRACE / "out-landmark-quest/handoff.json"


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not REPORT.is_file():
        print("PENDING controlled OUT landmark quest")
        return 0
    source = json.loads((TRACE / "out-first-input/handoff.json").read_text())
    trial = json.loads(REPORT.read_text())
    require(trial["source_snapshot"] == source["snapshot"] and
            trial["working_game_disk"] == source["working_game_disk"],
            "landmark quest ancestry differs")
    prior, completed = checked(source["snapshot"]), checked(trial["snapshot"])
    require(trial["interventions"] ==
            [{"address": "0x0000", "before": [39, 33], "after": [59, 3]},
             {"address": "0x7EA9", "before": 0, "after": 1}] and
            trial["initial"] == {"position": [39, 33], "quest": [0] * 8,
                                 "target_tile": 0x0A} and
            prior[0x6000 + 3 * 64 + 59] == 0x0A and trial["input"] == 69,
            "landmark state or controlled input differs")
    require([point["pc"] for point in trial["checkpoints"]] ==
            ["0x90C8", "0x913A", "0x915F", "0x9162"] and
            " a=02 " in trial["checkpoints"][1]["cpu"] and
            " a=FF " in trial["checkpoints"][3]["cpu"],
            "landmark completion path differs")
    require(trial["state"] == {"world_location": 2,
                               "quest": [0xFF] + [0] * 7,
                               "position": [59, 3]} and
            list(completed[0x7EA9:0x7EB1]) == trial["state"]["quest"] and
            completed[0x7EED] == 2 and
            list(completed[:2]) == [59, 3],
            "landmark completion result differs")
    print("OUT landmark (59,3), E: accepted even quest 0 changed 1→$FF")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"landmark quest verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
