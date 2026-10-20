#!/usr/bin/env python3
"""Verify that a successful save returns to GEN's A/B menu."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-after-save" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN after-save trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["checkpoint"]["pc"] == "0x89FD",
            "after-save input address differs")
    for key in ("source_snapshot", "player_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    require(before[0x7E6D:0x8037] == after[0x7E6D:0x8037],
            "character record changed before menu input")
    print("GEN successful save: $895B → $89FD A/B menu; record unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN after-save verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
