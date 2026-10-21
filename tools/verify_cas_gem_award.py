#!/usr/bin/env python3
"""Check controlled completed odd quest reporting and red gem award."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
REPORT = TRACE / "cas-gem-award/handoff.json"


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not REPORT.is_file():
        print("PENDING controlled CAS gem award")
        return 0
    source = json.loads((TRACE / "cas-first-input/handoff.json").read_text())
    trial = json.loads(REPORT.read_text())
    require(trial["source_snapshot"] == source["snapshot"] and
            trial["working_game_disk"] == source["working_game_disk"],
            "gem award ancestry differs")
    prior, awarded = checked(source["snapshot"]), checked(trial["snapshot"])
    require(trial["initial"] == {"position": [0, 9], "index": 6,
                                 "quest": [0] * 8, "gems": [0] * 4,
                                 "group": 0} and
            trial["interventions"] ==
            [{"address": "0x0000", "before": [0, 9], "after": [31, 6]},
             {"address": "0x9E3B", "before": 6, "after": 1},
             {"address": "0x7EAA", "before": 0, "after": 255}] and
            prior[0xB400 + 6 * 38 + 31] == 0x6C and trial["input"] == 84,
            "controlled gem-award prerequisites differ")
    require([point["pc"] for point in trial["checkpoints"]] ==
            ["0x92AA", "0x92CC", "0x94E7", "0x959D", "0x95BC",
             "0x963A", "0x963D"] and
            " a=FF " in trial["checkpoints"][2]["cpu"],
            "completed odd quest did not take gem path")
    require(trial["final"] == {"quest": [0] * 8,
                               "gems": [1, 0, 0, 0], "index": 1} and
            list(awarded[0x7EA9:0x7EB1]) == [0] * 8 and
            list(awarded[0x7E75:0x7E79]) == [1, 0, 0, 0],
            "quest reset or red gem counter differs")
    print("CAS completed odd quest 1: T reset $7EAA $FF→0 and red gem $7E75 0→1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"castle gem verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
