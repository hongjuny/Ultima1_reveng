#!/usr/bin/env python3
"""Verify controlled lethal guard damage and OUT resurrection."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
DEATH = TRACE / "cas-guard-death" / "handoff.json"
OUT = TRACE / "cas-death-to-out" / "handoff.json"


def checked_ram(item: dict) -> bytearray:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "controlled death snapshot differs")
    return main_ram(path)


def main() -> int:
    if not DEATH.is_file() or not OUT.is_file():
        print("PENDING CAS controlled death and OUT resurrection")
        return 0
    prior = json.loads((TRACE / "cas-attack-effect" / "handoff.json").read_text())
    death = json.loads(DEATH.read_text())
    out = json.loads(OUT.read_text())
    require(death["timeout"] is None and
            death["source_snapshot"] == prior["handler_return_snapshot"] and
            death["working_game_disk"] == prior["working_game_disk"] and
            death["controlled_change"] ==
            {"address": "0x7EC6", "before": 0x96, "after": 0x0A},
            "controlled death ancestry or HP change differs")
    pre = checked_ram(death["intervention_snapshots"]["before"])
    post = checked_ram(death["intervention_snapshots"]["after"])
    require([(address, pre[address], post[address])
             for address in range(0x10000) if pre[address] != post[address]] ==
            [(0x7EC6, 0x96, 0x0A)] and pre[0x73] == post[0x73] == 0x0F,
            "intervention changed more than player HP low byte")
    points = death["checkpoints"]
    require([point["pc"] for point in points] ==
            ["0x99CB", "0x99D4", "0x99DC", "0x8A41", "0x88F8", "0x88FD"] and
            [point["hp"] for point in points] ==
            [[0x96, 0], [0xFB, 0], [0xFB, 0xFF],
             [0xFB, 0xFF], [0xFB, 0xFF], [0, 0]] and
            not (int(points[2]["cpu"].split(" p=")[1][:2], 16) & 1) and
            " a=04 " in points[-1]["cpu"],
            "lethal subtract or OUT selection differs")
    death_ram = checked_ram(death["snapshot"])
    require(death_ram[0x7EC6:0x7EC8] == bytes((0, 0)) and
            death_ram[0x7EE5:0x7EE7] == bytes((0, 0)) and
            death["final_cpu"] == points[-1]["cpu"],
            "selector state after death differs")
    require(out["timeout"] is None and
            out["source_snapshot"] == death["snapshot"] and
            out["working_game_disk"] == death["working_game_disk"],
            "resurrection OUT ancestry differs")
    require([point["pc"] for point in out["checkpoints"]] ==
            ["0x8920", "0x892B", "0x8956", "0x898A", "0x89E8",
             "0x8A3A", "0x8A47", "0x8995", "0x89A1", "0x8A6C"] and
            out["filename"] == "OUT" and out["memory_match_at_load"] is True and
            out["out_bytes"] == len((ROOT / "extracted" / "OUT").read_bytes()),
            "OUT reload or resurrection path differs")
    checks = out["checkpoints"]
    require(checks[3]["position"] == checks[4]["position"] == [30, 31] and
            checks[4]["health"] == checks[4]["food"] == [0, 0] and
            checks[5]["position"] == [3, 8] and
            checks[5]["health"] == checks[5]["food"] == [0, 0] and
            checks[6]["health"] == [99, 0] and checks[6]["food"] == [0, 0] and
            checks[7]["health"] == checks[7]["food"] == [99, 0],
            "resurrection initialization checkpoints differ")
    final = checked_ram(out["snapshot"])
    require(final[0:2] == bytes((3, 8)) and
            final[0x7EC6:0x7EC8] == final[0x7EE5:0x7EE7] == bytes((99, 0)) and
            out["final_cpu"] == checks[-1]["cpu"],
            "resurrected OUT first input differs")
    print("CAS controlled death: HP $000A − $000F borrowed → $8A41 → OUT")
    print("OUT resurrection: (3,8), HP=$0063, food=$0063 at first input")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS controlled death verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
