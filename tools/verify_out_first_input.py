#!/usr/bin/env python3
"""Verify OUT initialization reached its first bounded keyboard poll."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-first-input" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT first-input trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "OUT initialization timed out")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x898A", "0x89A1", "0x8A6C"],
            "OUT initialization checkpoints differ")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at input poll")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-entry" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "input trace does not descend from OUT entry")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0x15C5:0x15C8] == bytes.fromhex("4c a3 1d") and
            report["state"]["poll_stub_15C5"] == "4ca31d",
            "input stub differs")
    require(ram[0x8A6A:0x8A76] ==
            (ROOT / "extracted" / "OUT").read_bytes()[0x8A6A-0x8956:0x8A76-0x8956],
            "input poll bytes differ")
    require(report["state"]["health_7EC6_7EC7"] == "9600" and
            report["state"]["food_7EE5_7EE6"] == "c800",
            "initial outdoor health/food differ")
    print("OUT: $898A initialization → $89A1 main loop → $8A6C first input poll")
    print("OUT: health=$0096, food=$00C8; $15C5 jumps to STUPH $1DA3")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT first-input verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
