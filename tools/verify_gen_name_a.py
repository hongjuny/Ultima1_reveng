#!/usr/bin/env python3
"""Verify the observed one-character GEN name and confirmation handoff."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-name-a" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN name A trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == [
        {"key_ascii": 65, "at_pc": "0x8E83"},
        {"key_ascii": 13, "at_pc": "0x8E83"},
    ], "name input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8EC7", "0x8E83", "0x8EEE"],
            "name checkpoint sequence differs")
    for item in (report["source_snapshot"], report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "name snapshot differs from report")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    require(before[0x9042] == 0 and after[0x9042] == 1,
            "name length did not become one")
    require(after[0x7EB8] == 65 and report["name_ascii"] == [65],
            "name A was not stored at $7EB8")
    require([after[a] for a in range(0x7EC8, 0x7ED4, 2)] ==
            [35, 35, 10, 10, 10, 15], "attributes changed during name input")
    print("GEN name A: length=1, $7EB8=$41; Return reaches $8EEE")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN name-A verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
