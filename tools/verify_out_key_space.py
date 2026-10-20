#!/usr/bin/env python3
"""Verify Space selects the fifth outdoor command handler."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require
from verify_out_ram_attempt import register


REPORT = ROOT / "build" / "traces" / "out-key-space" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT key Space trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "OUT Space trace timed out")
    require(report["input"] == {"key_ascii": 32, "at_pc": "0x8A6C"},
            "OUT Space input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8A74", "0x89CB", "0x89CE", "0x89D0"],
            "OUT Space checkpoints differ")
    require(register(report["checkpoints"][0]["cpu"], "a") == 0x20 and
            register(report["checkpoints"][1]["cpu"], "x") == 0x20,
            "Space was not passed to command lookup")
    require(not status_carry(report["checkpoints"][2]["cpu"]) and
            register(report["checkpoints"][2]["cpu"], "x") == 8,
            "Space lookup did not return table offset 8")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at handler selection")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-first-input" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "Space trace does not descend from first input")
    ram = main_ram(Path(report["snapshot"]["path"]))
    out = (ROOT / "extracted" / "OUT").read_bytes()
    require(ram[0x9AAA + 8:0x9AAA + 10] == bytes((0x76, 0x8A)),
            "Space handler pointer is not $8A76")
    require(ram[0x8A76:0x8A7D] == out[0x8A76-0x8956:0x8A7D-0x8956],
            "Space handler bytes differ")
    print("OUT Space: command table index 4, handler pointer $8A76, carry clear")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT key-Space verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
