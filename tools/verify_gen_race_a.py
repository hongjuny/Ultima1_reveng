#!/usr/bin/env python3
"""Verify GEN race A and the handoff to sex selection."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-race-a" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN race A trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_ascii": 65, "at_pc": "0x8CD0"},
            "race input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8CFA", "0x8D3C", "0x8D72"], "race checkpoint sequence differs")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "race snapshot differs from report")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    expected = [25, 25, 10, 10, 10, 15]
    require([before[a] for a in range(0x7EC8, 0x7ED4, 2)] ==
            [25, 25, 10, 10, 10, 10], "pre-race attributes differ")
    require([after[a] for a in range(0x7EC8, 0x7ED4, 2)] == expected and
            after[0x7ED6] == 1, "race A bonus or ID differs")
    require(report["attributes_after_bonus"] == expected,
            "reported race attributes differ")
    print("GEN race A: $7ED6=1, sixth attribute 10→15")
    print("GEN next input: $8D72 sex choice A/B")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN race-A verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
