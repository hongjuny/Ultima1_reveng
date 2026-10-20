#!/usr/bin/env python3
"""Verify castle data loads, three-page map copy, and first key poll."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
REPORT = TRACE / "cas-first-input" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING CAS first-input trace")
        return 0
    report = json.loads(REPORT.read_text())
    prior = json.loads((TRACE / "out-to-cas" / "handoff.json").read_text())
    require(report["timeout"] is None and
            report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "CAS first-input ancestry or runtime differs")
    require([point["pc"] for point in report["checkpoints"]] ==
            ["0x898D", "0x89A3", "0x89CE", "0x8A31", "0x8A27"],
            "CAS initialization checkpoints differ")
    require(report["tcmaps_match"] is True and
            report["mapchars_match"] is True and
            report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "CAS loader match or final poll differs")
    item = report["snapshot"]
    snapshot = Path(item["path"])
    require(describe(snapshot) ==
            {"size": item["size"], "sha256": item["sha256"]},
            "CAS first-input snapshot differs")
    ram = main_ram(snapshot)
    maps = (ROOT / "extracted" / "TCMAPS").read_bytes()
    chars = (ROOT / "extracted" / "MAPCHARS").read_bytes()
    require(ram[0x4000:0x4000 + len(maps)] == maps and
            ram[0xB000:0xB000 + len(chars)] == chars,
            "CAS loaded data differs at first input")
    require(ram[0xB400:0xB700] == maps[20:20 + 768],
            "CAS map copy is not first 768 bytes from record 0")
    require(maps[20:20 + 764] == ram[0xB400:0xB400 + 764] and
            maps[20 + 764:20 + 768] == ram[0xB400 + 764:0xB700],
            "CAS map copy did not extend four bytes into record 1")
    print("CAS: TCMAPS and MAPCHARS loaded byte-for-byte")
    print("CAS: $4014-$4313 → $B400-$B6FF, including 4 bytes of next record")
    print("CAS: $8A27 first key poll")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS first-input verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
