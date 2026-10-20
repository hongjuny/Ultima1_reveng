#!/usr/bin/env python3
"""Verify Space returns to the outdoor poll without another state update."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-after-space" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT after-Space trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "OUT after-Space trace timed out")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8995", "0x89A1", "0x8A6C"],
            "OUT return-to-input checkpoints differ")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at outdoor poll")
    require(report["watched_before"] == report["watched_after"],
            "watched state changed after handler return")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-space-effect" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "continuation does not descend from Space handler")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    for label, value in report["watched_before"].items():
        address = int(label[1:], 16)
        require(before[address] == after[address] == value,
                f"snapshot state changed at {label}")
    print("OUT Space: $89DF → $8995 → $89A1 → $8A6C; watched state stable")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT after-Space verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
