#!/usr/bin/env python3
"""Verify class A's observed attribute bonuses and name-input handoff."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-class-a" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN class A trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_ascii": 65, "at_pc": "0x8DEA"},
            "class input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8E12", "0x8E54", "0x8E83"], "class checkpoint sequence differs")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "class snapshot differs from report")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    require([before[a] for a in range(0x7EC8, 0x7ED4, 2)] ==
            [25, 25, 10, 10, 10, 15], "pre-class attributes differ")
    require([after[a] for a in range(0x7EC8, 0x7ED4, 2)] ==
            [35, 35, 10, 10, 10, 15], "class A bonuses differ")
    require(after[0x7ED8] == 1, "class A ID differs")
    require(after[0x9042] == 0, "name length is not initially zero")
    require(report["attributes_after_bonus"] == [35, 35, 10, 10, 10, 15],
            "reported class attributes differ")
    print("GEN class A: $7ED8=1, first two attributes 25→35; name input at $8E83")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN class-A verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
