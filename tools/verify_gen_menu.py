#!/usr/bin/env python3
"""Verify the private GEN menu snapshot and byte-reviewed input dispatch."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-menu" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN menu trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["checkpoint"]["pc"] == "0x89FD", "GEN menu PC differs")
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "GEN menu snapshot differs from report")
    ram = main_ram(path)
    gen = (ROOT / "extracted" / "GEN").read_bytes()
    require(ram[0x89FD:0x8A10] == gen[0x89FD - 0x8956:0x8A10 - 0x8956],
            "GEN menu dispatch bytes differ")
    print("GEN menu: $89FD key read, $89FD–$8A0F matches extraction")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN menu verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
