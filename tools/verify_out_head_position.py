#!/usr/bin/env python3
"""Verify the controlled head-position replay and loaded OUT image."""

import json
from pathlib import Path
import struct
import sys

from baseline import describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_out_disk_attempt import drive_head_offset
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-head-position" / "handoff.json"


def checked(item: dict, label: str) -> Path:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"{label} differs from report")
    return path


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT preserved-head trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None, "preserved-head replay timed out")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x16C8", "0x16FC", "0x892B"],
            "OUT load checkpoint sequence differs")
    require(all(not status_carry(p["cpu"]) for p in report["checkpoints"]),
            "OUT load returned carry set")
    require(report["final_cpu"] == report["checkpoints"][-1]["cpu"],
            "snapshot is not at the caller return")
    source = checked(report["source_snapshot"], "source snapshot")
    player_item = report["head_probe"]["player_snapshot"]
    player = checked(player_item, "player snapshot")
    patched = checked(report["head_probe"]["patched_snapshot"], "patched snapshot")
    final = checked(report["snapshot"], "final snapshot")
    checked(report["working_game_disk"], "game disk")
    prior = json.loads((ROOT / "build" / "traces" / "out-ram-attempt" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "head replay does not descend from RAM fallback")
    original = source.read_bytes()
    modified = patched.read_bytes()
    position = drive_head_offset(original)
    player_data = player.read_bytes()
    old = struct.unpack_from("<h", original, position)[0]
    new = struct.unpack_from("<h", modified, position)[0]
    player_head = struct.unpack_from("<h", player_data,
                                     drive_head_offset(player_data))[0]
    require((old, new, player_head) == (38, 2, 2),
            "head positions differ from controlled replay")
    require(original[:position] == modified[:position] and
            original[position + 2:] == modified[position + 2:],
            "snapshot patch changed more than the head position")
    require(report["head_probe"]["game_quarter_track"] == old and
            report["head_probe"]["preserved_quarter_track"] == new,
            "reported head positions differ")
    out = (ROOT / "extracted" / "OUT").read_bytes()
    ram = main_ram(final)
    require(ram[0x8956:0x8956 + len(out)] == out,
            "loaded OUT overlay differs from extraction")
    print(f"OUT: preserved head {old}→{new}, disk call returned carry clear; "
          f"all {len(out)} overlay bytes match at $8956")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT head-position verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
