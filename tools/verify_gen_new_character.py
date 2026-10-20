#!/usr/bin/env python3
"""Verify the private replay of GEN menu choice A."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-new-character" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN new-character trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_ascii": 65, "at_pc": "0x89FD"},
            "GEN menu input differs")
    point = report["checkpoint"]
    require(point["pc"] == "0x8AC3" and "a=41" in point["cpu"],
            "GEN choice A did not reach $8AC3 with A=$41")
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "new-character snapshot differs from report")
    ram = main_ram(path)
    gen = (ROOT / "extracted" / "GEN").read_bytes()
    require(ram[0x8AC3:0x8AC9] == gen[0x8AC3 - 0x8956:0x8AC9 - 0x8956],
            "new-character entry bytes differ")
    print("GEN choice A: $89FD → $8AC3 with A=$41; entry bytes match")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN choice verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
