#!/usr/bin/env python3
"""Check K on the first dungeon entrance tile through OUT reload."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-first-input/handoff.json"
EXIT = TRACE / "dng-exit-k/handoff.json"
OUT = TRACE / "dng-to-out/handoff.json"


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"dungeon exit snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, EXIT, OUT)):
        print("PENDING DNG K exit and OUT return")
        return 0
    source, exit_report, out = [json.loads(path.read_text())
                                for path in (SOURCE, EXIT, OUT)]
    require(all(item["timeout"] is None for item in (source, exit_report, out)) and
            exit_report["source_snapshot"] == source["snapshot"] and
            out["source_snapshot"] == exit_report["snapshot"] and
            exit_report["working_game_disk"] == out["working_game_disk"] ==
            source["working_game_disk"] and
            exit_report["input"] == {"key_ascii": 75, "at_pc": "0x8DDA"},
            "DNG K exit snapshot ancestry differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG exit game disk differs")
    start_ram = checked_ram(source["snapshot"])
    exit_ram = checked_ram(exit_report["snapshot"])
    out_ram = checked_ram(out["snapshot"])
    require(exit_report["before"] ==
            {"local_position": "0101", "facing": "0001", "depth": "01",
             "tile": "08", "hp": "9600", "saved_outdoor": "2b0f"} and
            exit_report["after"] ==
            {"local_position": "0101", "facing": "0001", "depth": "00",
             "hp": "9600", "saved_outdoor": "2b0f"} and
            [point["pc"] for point in exit_report["checkpoints"]] ==
            ["0x8DE4", "0x8DD7", "0x8E0B", "0x961B", "0x963F", "0x9666",
             "0x9670", "0x9697", "0x9716", "0x88FB", "0x88FD"] and
            start_ram[0xA52C:0xA52E] == b"\x00\x00" and
            exit_ram[0xA506] == 0 and
            exit_ram[0x7EC6:0x7EC8] == b"\x96\x00",
            "DNG K stair gate, depth, or exit state differs")
    require(out["filename"] == "OUT" and
            out["out_bytes"] == len((ROOT / "extracted/OUT").read_bytes()) == 5230 and
            out["memory_match_at_load"] is True and
            out["saved_coords_7E73"] == out["coords_after"] == "2b0f" and
            [point["pc"] for point in out["checkpoints"]] ==
            ["0x8920", "0x892B", "0x8956", "0x89A1", "0x8A6C"] and
            out_ram[0:2] == out_ram[0x7E73:0x7E75] == bytes((43, 15)) and
            out_ram[0x7EC6:0x7EC8] == b"\x96\x00" and
            out_ram[0x7EE5:0x7EE7] == b"\xB4\x00",
            "DNG-to-OUT overlay or restored state differs")
    print("DNG K on tile $08: depth 1→0, $9716→$88FB; HP $0096 unchanged")
    print("OUT reload: all 5230 bytes match; (43,15), HP $0096, food $00B4 at first input")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG exit verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
