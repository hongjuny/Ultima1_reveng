#!/usr/bin/env python3
"""Verify Space's handler path and the immediate shared-state update."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-space-effect" / "handoff.json"
EXPECTED_BEFORE = {"$7E4F": 5, "$7E50": 80, "$7EDA": 0, "$7EE4": 149,
                   "$7EE5": 200, "$7EE6": 0, "$7EC6": 150, "$7EC7": 0}
EXPECTED_AFTER = {**EXPECTED_BEFORE, "$7EDA": 80, "$7EE4": 144}


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT Space-effect trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "Space handler trace timed out")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x89DC", "0x8A76", "0x82E2", "0x89DF"],
            "Space handler checkpoints differ")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at handler return")
    require(report["watched_before"] == EXPECTED_BEFORE and
            report["watched_after"] == EXPECTED_AFTER,
            "Space state update differs")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-key-space" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "handler trace does not descend from Space dispatch")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    for address in (0x7E4F, 0x7E50, 0x7EDA, 0x7EE4, 0x7EE5, 0x7EE6,
                    0x7EC6, 0x7EC7):
        label = f"${address:04X}"
        require(before[address] == EXPECTED_BEFORE[label] and
                after[address] == EXPECTED_AFTER[label],
                f"snapshot state differs at {label}")
    require(after[0x89DC:0x89DF] == bytes((0x20, 0x76, 0x8A)),
            "self-modified command call does not target $8A76")
    print("OUT Space: $8A76 → $82E2 → $89DF; $7EE4 $95→$90, $7EDA $00→$50")
    print("OUT Space: health $0096 and food $00C8 unchanged at handler return")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT Space-effect verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
