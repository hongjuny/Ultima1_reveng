#!/usr/bin/env python3
"""Verify the common selector entered the loaded OUT overlay."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-entry" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT entry trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "OUT entry trace timed out")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x892E", "0x893C", "0x8956"],
            "OUT entry checkpoints differ")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at OUT entry")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-head-position" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "OUT entry does not descend from verified load")
    out = (ROOT / "extracted" / "OUT").read_bytes()
    require(report["out_bytes"] == len(out), "OUT byte count differs")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0x8956:0x8956 + len(out)] == out,
            "OUT entry image differs from extraction")
    print("OUT: $892E → $893C → $8956; all 5230 overlay bytes match at entry")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT entry verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
