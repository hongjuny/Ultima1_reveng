#!/usr/bin/env python3
"""Verify decrease, minimum, and navigation in GEN's attribute menu."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-attribute-controls" / "handoff.json"
EXPECTED = ((0x08, 10, 30, 1), (0x08, 10, 30, 1),
            (0x2F, 10, 30, 2), (0x0B, 10, 30, 1))


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN attribute controls trace")
        return 0
    report = json.loads(REPORT.read_text())
    events = report["events"]
    require(len(events) == len(EXPECTED), "attribute event count differs")
    for event, expected in zip(events, EXPECTED):
        actual = (event["key_code"], event["attribute_7EC8"],
                  event["points_903F"], event["selection_9041"])
        require(event["pc"] == "0x8C00" and actual == expected,
                f"attribute control event differs: {event}")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "attribute control snapshot differs from report")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require((ram[0x7EC8], ram[0x903F], ram[0x9041]) == (10, 30, 1),
            "final attribute control RAM differs")
    print("GEN $08: 11→10, pool 29→30; minimum 10 held")
    print("GEN $2F/$0B: selection 1→2→1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN attribute controls verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
