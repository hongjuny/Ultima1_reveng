#!/usr/bin/env python3
"""Verify that P reaches the outdoor command lookup's unknown-key path."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require
from verify_out_ram_attempt import register


REPORT = ROOT / "build" / "traces" / "out-key-p" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT key P trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "OUT key P trace timed out")
    require(report["input"] == {"key_ascii": 80, "at_pc": "0x8A6C"},
            "OUT input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8A74", "0x89CB", "0x89CE", "0x89DF"],
            "OUT P checkpoints differ")
    require(register(report["checkpoints"][0]["cpu"], "a") == 0x50 and
            register(report["checkpoints"][1]["cpu"], "x") == 0x50,
            "P was not passed to command lookup")
    require(status_carry(report["checkpoints"][2]["cpu"]) and
            register(report["checkpoints"][2]["cpu"], "x") == 0xFF,
            "P lookup did not return the unknown-key result")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at the unknown-key branch")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-first-input" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "P trace does not descend from first input")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    table = after[0x7E53:0x7E53 + 26]
    require(table == (ROOT / "extracted" / "MI.U1").read_bytes()
            [0x7E53-0x7000:0x7E53-0x7000 + 26],
            "shared command table differs")
    require(0x50 not in table and 0x20 in table,
            "P/Space command table membership differs")
    require(before[0x7EC6:0x7EC8] == after[0x7EC6:0x7EC8] and
            before[0x7EE5:0x7EE7] == after[0x7EE5:0x7EE7],
            "health or food changed before unknown-key branch")
    print("OUT P: poll returned $50; command table has no P; lookup set carry and skipped handler")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT key-P verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
