#!/usr/bin/env python3
"""Verify the first GEN attribute increase in a private replay snapshot."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-attribute-increase" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN attribute increase trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_code": 0x15, "at_pc": "0x8C07"},
            "attribute input differs")
    require(report["checkpoint"]["pc"] == "0x8C00", "attribute loop PC differs")
    require(report["before"] == {"attribute_7EC8": 10, "points_903F": 30,
                                 "selection_9041": 1}, "initial attribute state differs")
    require(report["after"] == {"attribute_7EC8": 11, "points_903F": 29,
                                "selection_9041": 1}, "increased attribute state differs")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "attribute snapshot differs from report")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    require((before[0x7EC8], before[0x903F], before[0x9041]) == (10, 30, 1),
            "initial RAM values differ")
    require((after[0x7EC8], after[0x903F], after[0x9041]) == (11, 29, 1),
            "increased RAM values differ")
    print("GEN $15: first attribute 10→11, unassigned points 30→29")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN attribute increase verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
