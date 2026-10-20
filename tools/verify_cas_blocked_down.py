#!/usr/bin/env python3
"""Verify an accepted castle down step followed by a blocked wall step."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
BASE = TRACE / "cas-blocked-down"


def main() -> int:
    if not (BASE / "step-02" / "handoff.json").is_file():
        print("PENDING CAS blocked-down trace")
        return 0
    previous = json.loads((TRACE / "cas-first-input" / "handoff.json").read_text())
    cases = ((1, "0x8C29", 0x60, True, (0, 9), (0, 10), 0x45, 0x44),
             (2, "0x8C13", 0x40, False, (0, 10), (0, 10), 0x44, 0x43))
    for number, branch, tile, carry, before_xy, after_xy, before_clock, after_clock in cases:
        report = json.loads((BASE / f"step-{number:02d}" / "handoff.json").read_text())
        require(report["timeout"] is None and
                report["source_snapshot"] == previous["snapshot"] and
                report["working_game_disk"] == previous["working_game_disk"],
                f"castle step {number} ancestry differs")
        require(report["input"] == {"key_ascii": 10, "at_pc": "0x8A27"},
                f"castle step {number} key differs")
        require([point["pc"] for point in report["checkpoints"]] ==
                ["0x8A2F", "0x8A4A", "0x8A56", "0x8A9A", "0x8C00",
                 "0x8C11", branch, "0x8C3F", "0x8A59", "0x8A31", "0x8A27"],
                f"castle step {number} path differs")
        collision = report["collision_cpu"]
        require(collision is not None and f" a={tile:02X} " in collision and
                bool(int(collision.split(" p=")[1][:2], 16) & 1) == carry,
                f"castle step {number} collision result differs")
        item = report["snapshot"]
        snapshot = Path(item["path"])
        require(describe(snapshot) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"castle step {number} snapshot differs")
        before = main_ram(Path(previous["snapshot"]["path"]))
        after = main_ram(snapshot)
        require((before[0], before[1]) == before_xy and
                (after[0], after[1]) == after_xy,
                f"castle step {number} position differs")
        require((before[0x7EE4], after[0x7EE4]) == (before_clock, after_clock) and
                (before[0x7EDA], after[0x7EDA]) == (16 * (number - 1), 16 * number),
                f"castle step {number} turn differs")
        require(after[0x7EC6:0x7EC8] == before[0x7EC6:0x7EC8] and
                after[0x7EE5:0x7EE7] == before[0x7EE5:0x7EE7],
                f"castle step {number} health or food changed")
        require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
                f"castle step {number} did not return to input")
        previous = report
    ram = main_ram(Path(previous["snapshot"]["path"]))
    require(ram[0xB400 + 10 * 38] == 0x60 and
            ram[0xB400 + 11 * 38] == 0x40,
            "castle map tiles differ at x=0, y=10/11")
    print("CAS down: (0,9) → (0,10) on $60, then $40 blocks (0,11)")
    print("blocked turn: position fixed; $7EE4 $44→$43, $7EDA $10→$20")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS blocked-down verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
