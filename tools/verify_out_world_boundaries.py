#!/usr/bin/env python3
"""Check four controlled world crossings against private runtime evidence."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_out_world_boundaries import CASES, OUTPUT, SOURCE


EXPECTED = {
    "east": (1, 0x40, 0xF6, 0x20),
    "west": (3, 0xC0, 0x48, 0x20),
    "south": (2, 0x80, 0x27, 0xFB),
    "north": (2, 0x80, 0x27, 0x43),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING controlled four-edge OUT replay")
        return 0
    report = json.loads(path.read_text())
    prior = json.loads(SOURCE.read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "OUT source lineage changed")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private input changed")
    require(set(report["runs"]) == set(CASES), "edge set changed")
    for name, (address, value, edge_pc) in CASES.items():
        run = report["runs"][name]
        label = f"${address:04X}"
        before, changed = run["before_intervention"], run["intervened"]
        index, bits, x, y = EXPECTED[name]
        require(run["key"] == 11 and run["patch_address"] == label and
                run["patch_value"] == value and
                run["edge_pc"] == f"${edge_pc:04X}", f"{name}: input changed")
        require([point["pc"] for point in run["points"]] ==
                ["0x8A74", "0x9416", "0x9477", f"0x{edge_pc:04X}",
                 "0x94C1", "0x9503", "0x952C", "0x8A6C"],
                f"{name}: execution path changed")
        require({key: item for key, item in changed.items()
                 if item != before[key]} == {label: value},
                f"{name}: intervention changed more than one byte")
        require((before["$000C"], before["$000D"],
                 before["$7E6F"], before["$7E70"]) == (0x27, 0x20, 0, 0),
                f"{name}: starting state changed")
        raw_index = {"east": 1, "west": 0xFF,
                     "south": 0xFE, "north": 2}[name]
        require((run["masked"]["$0000"], run["masked"]["$0001"],
                 run["masked"]["$7E6F"]) == (x, y, raw_index),
                f"{name}: coordinate or segment mismatch")
        require(run["encoded_before"]["$7E70"] == 0 and
                (run["encoded"]["$7E6F"], run["encoded"]["$7E70"]) ==
                (index, bits), f"{name}: world bits mismatch")
        require((run["final"]["$7E6F"], run["final"]["$7E70"],
                 run["final"]["$0000"], run["final"]["$0001"]) ==
                (index, bits, x, y) and
                run["final_cpu"].startswith("pc=8A6C") and
                run["map_initial_sha256"] != run["map_after_sha256"],
                f"{name}: final map or state mismatch")
        print(f"OUT {name}: segment 0→{index}, XY=(${x:02X},${y:02X}), "
              f"bits=${bits:02X}, map changed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT four-edge verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
