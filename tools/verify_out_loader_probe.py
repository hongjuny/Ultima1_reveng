#!/usr/bin/env python3
"""Verify OUT selection reached STUPH's /RAM/OUT lookup."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-loader-probe" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT loader probe")
        return 0
    report = json.loads(REPORT.read_text())
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8920", "0x8928", "0x16AD"],
            "OUT loader probe checkpoints differ")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    require(report["working_game_disk"]["sha256"] ==
            report["boot_media"]["sha256"],
            "game disk copy changed during probe")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0x7E16:0x7E1A] == b"OUT\x00" and
            ram[0xBA79:0xBA7D] == b"\x03OUT",
            "OUT filename was not installed")
    require(ram[0x1703:0x170D] == b"\x80/RAM/OUT\x00" and
            ram[0xBF98] & 0x30 == 0x30,
            "RAM-disk lookup condition differs")
    print("OUT selector: relative OUT filename installed; /RAM/OUT tried first")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"OUT loader-probe verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
