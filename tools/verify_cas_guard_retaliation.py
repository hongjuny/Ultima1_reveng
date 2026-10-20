#!/usr/bin/env python3
"""Verify the guard retaliation path and exact player HP write."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
REPORT = TRACE / "cas-guard-retaliation" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING CAS guard retaliation trace")
        return 0
    prior = json.loads((TRACE / "cas-attack-effect" / "handoff.json").read_text())
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None and
            report["source_snapshot"] == prior["handler_return_snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "guard retaliation ancestry differs")
    source = report["source_snapshot"]
    snapshot = Path(source["path"])
    require(describe(snapshot) == {"size": source["size"], "sha256": source["sha256"]},
            "guard source snapshot differs")
    before = main_ram(snapshot)
    item = report["snapshot"]
    snapshot = Path(item["path"])
    require(describe(snapshot) == {"size": item["size"], "sha256": item["sha256"]},
            "guard result snapshot differs")
    after = main_ram(snapshot)
    points = report["checkpoints"]
    require([point["pc"] for point in points] ==
            ["0x9804", "0x9933", "0x998F", "0x99CB", "0x99D4", "0x8A27"],
            "guard response path differs")
    require(before[0x9E2A] == 1 and before[0x7ECC] == 0x0A and
            before[0x7E7B] == 1 and before[0x7EC7] == 0 and
            points[2]["watched"]["$0072"] == 0x45 and
            " a=9D " in points[2]["cpu"],
            "guard hit threshold or roll differs")
    require(points[3]["watched"]["$0072"] == 0x14 and
            points[3]["watched"]["$0073"] == 0x0F and
            points[3]["watched"]["$7EC6"] == 0x96 and
            points[4]["watched"]["$7EC6"] == 0x87,
            "guard damage roll or HP store differs")
    require((before[0x7EC6], before[0x7EC7], after[0x7EC6], after[0x7EC7]) ==
            (0x96, 0, 0x87, 0) and
            before[0:2] == after[0:2] == bytes((1, 7)) and
            before[0xB6DE:0xB6DF] == after[0xB6DE:0xB6DF] and
            before[0xB6EE] == after[0xB6EE] and
            before[0x7EE4] == after[0x7EE4] and
            before[0x7EDA] == after[0x7EDA] and
            before[0x7EE5:0x7EE7] == after[0x7EE5:0x7EE7],
            "guard result state differs")
    original = main_ram(Path(prior["snapshot"]["path"]))
    require(report["final_cpu"] == points[-1]["cpu"] == prior["final_cpu"] and
            after == original,
            "guard trace did not reproduce original next-poll CPU and RAM")
    print("CAS guard: $9804 → $9933, hit roll $9D >= $45")
    print("guard damage $0F < $14; $99D1 stored player HP $96→$87")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS guard retaliation verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
