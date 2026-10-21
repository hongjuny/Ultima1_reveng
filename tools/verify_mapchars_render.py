#!/usr/bin/env python3
"""Verify MAPCHARS' live font swap and first castle glyph renderer."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
REPORT = TRACE / "mapchars-render/handoff.json"


def main():
    if not REPORT.is_file():
        print("PENDING MAPCHARS castle render")
        return 0
    report = json.loads(REPORT.read_text())
    prior = json.loads((TRACE / "tcmaps-last-slot/handoff.json").read_text())
    require(report["source_snapshot"] == prior["trials"]["ordinary"]["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"] and
            [int(p["cpu"].split()[0].split("=")[1], 16)
             for p in report["checkpoints"]] ==
            [0x9B06, 0x9B09, 0x9B0C, 0x1A58, 0x9B35, 0x9B38, 0x8A27],
            "MAPCHARS render ancestry or checkpoints differ")
    chars = (ROOT / "extracted/MAPCHARS").read_bytes()
    support = (ROOT / "extracted/STUPH").read_bytes()
    castle = (ROOT / "extracted/CAS").read_bytes()
    require(len(chars) == 1024 and support[0x1A58-0x0800:0x1A5B-0x0800] ==
            bytes.fromhex("b90008") and
            castle[0x9B06-0x8956:0x9B0C-0x8956] ==
            bytes.fromhex("20a715206e9b") and
            castle[0x9B35-0x8956:0x9B38-0x8956] ==
            bytes.fromhex("206e9b"),
            "MAPCHARS renderer or swap opcodes differ")
    flags = [(p["font_0800_matches_mapchars"], p["font_b000_matches_mapchars"])
             for p in report["checkpoints"]]
    require(flags == [(False, True), (False, True), (True, False),
                      (True, False), (True, False), (False, True),
                      (False, True)] and
            report["checkpoints"][3]["renderer_operand"] == "b90008" and
            " y=40 " in report["checkpoints"][3]["cpu"] and
            report["checkpoints"][2]["video_2000_sha256"] !=
            report["checkpoints"][4]["video_2000_sha256"] and
            report["final_cpu"].startswith("pc=8A27"),
            "MAPCHARS live font or first glyph differs")
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "MAPCHARS final snapshot changed")
    ram = main_ram(path)
    require(ram[0xB000:0xB400] == chars and
            ram[0x0800:0x0C00] != chars,
            "MAPCHARS font was not restored at first input")
    print("CAS: MAPCHARS $B000→$0800 during map draw; renderer $1A58 reads $0800,Y")
    print("CAS: font restored to $B000 before first input; video RAM changed during draw")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"MAPCHARS render verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
