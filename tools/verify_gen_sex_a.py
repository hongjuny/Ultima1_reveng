#!/usr/bin/env python3
"""Verify GEN sex A and the class-menu handoff."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-sex-a" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN sex A trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_ascii": 65, "at_pc": "0x8D72"},
            "sex input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8D83", "0x8DEA"], "sex-to-class checkpoint sequence differs")
    require(report["sex_id_7EB7"] == 0, "sex A ID differs")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "sex snapshot differs from report")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0x7EB7] == 0, "sex A RAM value differs")
    require([ram[a] for a in range(0x7EC8, 0x7ED4, 2)] ==
            [25, 25, 10, 10, 10, 15], "attributes changed before class choice")
    print("GEN sex A: $7EB7=0; class input at $8DEA")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN sex-A verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
