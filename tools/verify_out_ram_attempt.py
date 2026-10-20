#!/usr/bin/env python3
"""Verify the failed /RAM/OUT lookup and the disk fallback checkpoint."""

import json
from pathlib import Path
import re
import sys

from baseline import describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-ram-attempt" / "handoff.json"


def register(cpu: str, name: str) -> int:
    match = re.search(rf"\b{name}=([0-9A-Fa-f]{{2}})\b", cpu)
    if not match:
        raise ValueError(f"missing {name} in CPU state: {cpu}")
    return int(match.group(1), 16)


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT RAM lookup trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "RAM lookup trace timed out")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x16B2", "0x16B9"], "RAM lookup checkpoints differ")
    returned, fallback = report["checkpoints"]
    require(status_carry(returned["cpu"]) and register(returned["cpu"], "a") == 7,
            "/RAM/OUT did not return error $07 with carry")
    require(status_carry(fallback["cpu"]), "disk fallback was not entered with carry")
    require(report["final_cpu"] == fallback["cpu"],
            "snapshot was not saved at disk fallback")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-loader-probe" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "RAM lookup does not descend from OUT loader probe")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0x1703:0x170D] == b"\x80/RAM/OUT\x00" and
            ram[0x1709:0x170D] == b"OUT\x00",
            "fallback filename differs")
    print("OUT loader: /RAM/OUT returned error $07 with carry; relative OUT fallback reached")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"OUT RAM-attempt verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
