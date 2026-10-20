#!/usr/bin/env python3
"""Verify one accepted castle movement and its turn cost."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
REPORT = TRACE / "cas-step-right" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING CAS right-step trace")
        return 0
    report = json.loads(REPORT.read_text())
    prior = json.loads((TRACE / "cas-first-input" / "handoff.json").read_text())
    require(report["timeout"] is None and
            report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "castle movement ancestry differs")
    require(report["input"] == {"key_ascii": 21, "at_pc": "0x8A27"},
            "right key input differs")
    require([point["pc"] for point in report["checkpoints"]] ==
            ["0x8A2F", "0x8A4A", "0x8A56", "0x8AA1", "0x8C00",
             "0x8C11", "0x8C29", "0x8C3F", "0x8A59", "0x8A31", "0x8A27"],
            "accepted movement path differs")
    collision = report["collision_cpu"]
    require(collision is not None and " a=60 " in collision and
            int(collision.split(" p=")[1][:2], 16) & 1,
            "collision check did not return A=$60 carry set")
    item = report["snapshot"]
    snapshot = Path(item["path"])
    require(describe(snapshot) ==
            {"size": item["size"], "sha256": item["sha256"]},
            "castle movement snapshot differs")
    before = main_ram(Path(prior["snapshot"]["path"]))
    after = main_ram(snapshot)
    require((before[0], before[1], after[0], after[1]) == (0, 9, 1, 9),
            "castle position did not advance right")
    require((before[0x7EE4], after[0x7EE4], before[0x7EDA], after[0x7EDA]) ==
            (0x45, 0x44, 0x00, 0x10),
            "castle turn update differs")
    require(after[0x7EC6:0x7EC8] == before[0x7EC6:0x7EC8] and
            after[0x7EE5:0x7EE7] == before[0x7EE5:0x7EE7],
            "health or food changed on this step")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "castle movement did not return to input")
    print("CAS $15: collision A=$60 carry set, ($00,$09) → ($01,$09)")
    print("CAS turn: $7EE4 $45→$44, $7EDA $00→$10; health/food stable")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS right-step verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
