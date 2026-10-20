#!/usr/bin/env python3
"""Verify castle left-edge exit, OUT reload, and outdoor state restore."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
EXIT = TRACE / "cas-exit-left" / "handoff.json"
RETURN = TRACE / "cas-to-out" / "handoff.json"


def checked(path: Path) -> dict:
    report = json.loads(path.read_text())
    require(report["timeout"] is None, f"trace stopped: {path}")
    item = report["snapshot"]
    require(describe(Path(item["path"])) ==
            {"size": item["size"], "sha256": item["sha256"]},
            f"snapshot differs: {path}")
    return report


def main() -> int:
    if not EXIT.is_file() or not RETURN.is_file():
        print("PENDING CAS left-edge exit and OUT return")
        return 0
    castle = checked(TRACE / "cas-first-input" / "handoff.json")
    exit_report = checked(EXIT)
    return_report = checked(RETURN)
    require(exit_report["source_snapshot"] == castle["snapshot"] and
            exit_report["working_game_disk"] == castle["working_game_disk"],
            "castle exit ancestry differs")
    require(exit_report["input"] == {"key_ascii": 8, "at_pc": "0x8A27"},
            "castle exit key differs")
    require([point["pc"] for point in exit_report["checkpoints"]] ==
            ["0x8A2F", "0x8A4A", "0x8A56", "0x8AA8", "0x8AB3",
             "0x8BFD", "0x88FB", "0x88FD"],
            "castle left-edge path differs")
    require(exit_report["coords_before"] == exit_report["coords_after"] == "0009" and
            exit_report["edge_tile_B6BD"] == 0x23 and
            exit_report["saved_outdoor_coords"] == "1e1f" and
            " a=04 " in exit_report["final_cpu"],
            "castle exit state differs")
    print("CAS $08: x=0, $B6BD=$23 → $8BFD → $88FB with A=$04")

    require(return_report["source_snapshot"] == exit_report["snapshot"] and
            return_report["working_game_disk"] == exit_report["working_game_disk"],
            "OUT reload ancestry differs")
    require([point["pc"] for point in return_report["checkpoints"]] ==
            ["0x8920", "0x892B", "0x8956", "0x89A1", "0x8A6C"],
            "OUT reload path differs")
    require(return_report["filename"] == "OUT" and
            return_report["out_bytes"] == len((ROOT / "extracted" / "OUT").read_bytes()) and
            return_report["memory_match_at_load"] is True,
            "OUT overlay did not match at load")
    require(return_report["saved_coords_7E73"] ==
            return_report["coords_after"] == "1e1f" and
            return_report["final_cpu"] == return_report["checkpoints"][-1]["cpu"],
            "OUT coordinates or first poll differ")
    ram = main_ram(Path(return_report["snapshot"]["path"]))
    route = checked(TRACE / "out-route-to-04" / "step-11" / "handoff.json")
    route_ram = main_ram(Path(route["snapshot"]["path"]))
    require(ram[0:2] == ram[0x7E73:0x7E75] == route_ram[0:2] and
            ram[0x7EC6:0x7EC8] == route_ram[0x7EC6:0x7EC8] and
            ram[0x7EE5:0x7EE7] == route_ram[0x7EE5:0x7EE7],
            "OUT return did not retain coordinates/health/food")
    print("OUT reload: 5230 bytes matched; ($1E,$1F), health, food restored at $8A6C")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS exit verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
