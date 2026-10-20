#!/usr/bin/env python3
"""Verify failed save against the game disk and decode its inline arguments."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-confirm-yes" / "handoff.json"
PLAYER_PATH = b"/U1.PLAYER/U1.VARS"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN confirmation Y trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_ascii": 89, "at_pc": "0x8F12"},
            "save confirmation input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8F12", "0x8F23", "0x8F2C", "0x8F31"],
            "save checkpoint sequence differs")
    for item in (report["source_snapshot"], report["working_snapshot"],
                 report["snapshot"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "save snapshot differs from report")
    require(report["save_carry_set"] is True and
            status_carry(report["checkpoints"][2]["cpu"]),
            "failed save did not set carry")
    require(" a=06 " in report["checkpoints"][2]["cpu"],
            "failed save error code differs")
    require(describe(Path(report["working_disk"]["path"])) ==
            {"size": report["working_disk"]["size"],
             "sha256": report["working_disk"]["sha256"]},
            "working disk differs from report")
    require(report["working_disk"]["sha256"] == report["boot_media"]["sha256"],
            "failed save changed the working game disk")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0x7E38:0x7E38 + len(PLAYER_PATH)] == PLAYER_PATH,
            "player filename differs")
    require(ram[0xBA79] == len(PLAYER_PATH) and
            ram[0xBA7A:0xBA7A + len(PLAYER_PATH)] == PLAYER_PATH,
            "save helper did not copy player filename")
    require(ram[0xB73F:0xB743] == bytes((0x6D, 0x7E, 0xCA, 0x01)),
            "save source/length arguments differ")
    print("GEN save: $B724 source=$7E6D length=$01CA path=/U1.PLAYER/U1.VARS")
    print("GEN game-disk attempt: A=$06 carry set; $8F31 error branch; disk unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN confirmation-Y verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
