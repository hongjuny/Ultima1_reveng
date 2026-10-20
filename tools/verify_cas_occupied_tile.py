#!/usr/bin/env python3
"""Verify that a castle actor blocks an otherwise passable map tile."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
BASE = TRACE / "cas-occupied-tile"


def main() -> int:
    if not (BASE / "step-03" / "handoff.json").is_file():
        print("PENDING CAS occupied-tile trace")
        return 0
    previous = json.loads((TRACE / "cas-step-right" / "handoff.json").read_text())
    cases = ((1, (1, 9), (1, 8), "0x8C29", 0x60, True),
             (2, (1, 8), (1, 7), "0x8C29", 0x60, True),
             (3, (1, 7), (1, 7), "0x8C13", 0x33, False))
    for number, before_xy, after_xy, branch, result, carry in cases:
        report = json.loads((BASE / f"step-{number:02d}" / "handoff.json").read_text())
        require(report["timeout"] is None and
                report["source_snapshot"] == previous["snapshot"] and
                report["working_game_disk"] == previous["working_game_disk"],
                f"actor approach step {number} ancestry differs")
        require(report["input"] == {"key_ascii": 11, "at_pc": "0x8A27"},
                f"actor approach step {number} key differs")
        require([point["pc"] for point in report["checkpoints"]] ==
                ["0x8A2F", "0x8A4A", "0x8A56", "0x8A93", "0x8C00",
                 "0x8C11", branch, "0x8C3F", "0x8A59", "0x8A31", "0x8A27"],
                f"actor approach step {number} path differs")
        collision = report["collision_cpu"]
        require(collision is not None and f" a={result:02X} " in collision and
                bool(int(collision.split(" p=")[1][:2], 16) & 1) == carry,
                f"actor approach step {number} collision differs")
        item = report["snapshot"]
        snapshot = Path(item["path"])
        require(describe(snapshot) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"actor approach step {number} snapshot differs")
        before = main_ram(Path(previous["snapshot"]["path"]))
        after = main_ram(snapshot)
        require((before[0], before[1]) == before_xy and
                (after[0], after[1]) == after_xy,
                f"actor approach step {number} position differs")
        require((before[0x7EE4], after[0x7EE4]) == (0x45 - number, 0x44 - number) and
                (before[0x7EDA], after[0x7EDA]) == (16 * number, 16 * (number + 1)),
                f"actor approach step {number} turn differs")
        require(after[0x7EC6:0x7EC8] == before[0x7EC6:0x7EC8] and
                after[0x7EE5:0x7EE7] == before[0x7EE5:0x7EE7],
                f"actor approach step {number} health or food changed")
        require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
                f"actor approach step {number} did not return to input")
        if number == 3:
            require(before[0xB400 + 6 * 38 + 1] == 0x60 and
                    (before[0xB6BC + 2], before[0xB6CC + 2], before[0xB6AC + 2]) ==
                    (1, 6, 3) and after[0x9E36] == 2,
                    "passable tile or matching actor slot differs")
        previous = report
    print("CAS actor: passable $60 tile (1,6) occupied by slot 2/type 3")
    print("collision A=$33 carry clear; (1,7) fixed, turn $7EE4 $42→$41, $7EDA $30→$40")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS occupied-tile verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
