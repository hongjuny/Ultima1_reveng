#!/usr/bin/env python3
"""Verify GEN's state-template copy before its first character input."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-first-input" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN first-input trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["checkpoint"]["pc"] == "0x8C07", "first GEN input PC differs")
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "first-input snapshot differs from report")
    source = report["source_snapshot"]
    source_path = Path(source["path"])
    require(describe(source_path) == {"size": source["size"], "sha256": source["sha256"]},
            "new-character source snapshot differs")
    before = main_ram(source_path)
    after = main_ram(path)
    template = before[0x904F:0x90D7]
    require(len(template) == 136, "unexpected state template length")
    require(after[0x7E6F:0x7EF7] == template,
            "GEN state template did not copy to $7E6F–$7EF6")
    require(after[0x8B02:0x8B04] == bytes((0xD7, 0x90)) and
            after[0x8B05:0x8B07] == bytes((0xF7, 0x7E)),
            "copy loop's final self-modified operands differ")
    require(after[0x24] == 0x63 and after[0x903F] == 0x1E and
            after[0x9041] == 0x01, "first-input setup bytes differ")
    print("GEN copied 136 bytes $904F–$90D6 → $7E6F–$7EF6")
    print("GEN first input: PC=$8C07; $24=$63, $903F=$1E, $9041=$01")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN first-input verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
