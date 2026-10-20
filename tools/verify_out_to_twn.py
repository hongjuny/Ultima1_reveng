#!/usr/bin/env python3
"""Verify the outdoor code-$06 route, TWN load, and first town map copy."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
PATHS = (
    TRACE / "out-route-to-04" / "step-11" / "handoff.json",
    TRACE / "out-route-to-06" / "step-12" / "handoff.json",
    TRACE / "out-route-to-06" / "step-13" / "handoff.json",
    TRACE / "out-enter-06" / "handoff.json",
    TRACE / "out-to-twn" / "handoff.json",
    TRACE / "twn-first-input" / "handoff.json",
)


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "town-route snapshot differs")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in PATHS):
        print("PENDING OUT-to-TWN route and first-input trace")
        return 0
    start, left, down, enter, load, town = [json.loads(path.read_text()) for path in PATHS]
    reports = (start, left, down, enter, load, town)
    require(all(report["timeout"] is None for report in reports),
            "town route contains a stopped trace")
    require(all(reports[i]["snapshot"] == reports[i + 1]["source_snapshot"]
                for i in range(len(reports) - 1)) and
            all(report["working_game_disk"] == start["working_game_disk"]
                for report in reports),
            "town route snapshot or game-disk ancestry differs")
    disk = start["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "town route game disk differs")
    require(left["input"]["key_ascii"] == 0x08 and
            down["input"]["key_ascii"] == 0x0A and
            [(point["tile_lookup"]["x"], point["tile_lookup"]["y"],
              point["tile_lookup"]["raw"], point["tile_lookup"]["code"])
             for point in (left, down)] == [(29, 31, 2, 1), (29, 32, 12, 6)],
            "town route tile lookup differs")
    outdoor = checked_ram(down["snapshot"])
    require(outdoor[0:2] == bytes((29, 32)) and
            outdoor[0x6000 + 32 * 64 + 29] == 12,
            "town tile or outdoor position differs")
    require(enter["coords_before"] == enter["saved_coords_7E73"] == "1d20" and
            enter["nearby_tiles_7EB1"] == "01000100" and
            [point["pc"] for point in enter["checkpoints"]] ==
            ["0x8A74", "0x89CB", "0x89CE", "0x89D0", "0x89DC",
             "0x90C8", "0x90D5", "0x90FF", "0x9133", "0x8EFA", "0x88FD"] and
            " a=0C " in enter["final_cpu"],
            "town E dispatch or selector differs")
    require(load["filename"] == "TWN" and load["memory_match"] is True and
            load["twn_bytes"] == len((ROOT / "extracted" / "TWN").read_bytes()) and
            [point["pc"] for point in load["checkpoints"]] ==
            ["0x8920", "0x892B", "0x8956"],
            "town overlay load differs")
    require(town["tcmaps_match"] is True and town["mapchars_match"] is True and
            [point["pc"] for point in town["checkpoints"]] ==
            ["0x898B", "0x89A1", "0x89CC", "0x8A28", "0x8A1E"],
            "town data loads or first input differ")
    ram = checked_ram(town["snapshot"])
    tcmaps = (ROOT / "extracted" / "TCMAPS").read_bytes()
    require(ram[0xB400:0xB700] == tcmaps[20 + 2 * 764:20 + 2 * 764 + 768] and
            ram[0x7EED] == 13 and ram[0:2] == bytes((19, 17)) and
            ram[0x7ED4:0x7ED6] == bytes((100, 0)) and
            ram[0x7EE5:0x7EE7] == bytes((194, 0)),
            "town record-2 map copy or first-input state differs")
    print("OUT tile $06 at (29,32) → selector $0C → TWN, all 8461 bytes match")
    print("TWN first input: TCMAPS record 2 copied to $B400-$B6FF; Coin=100, food=194")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"OUT-to-TWN verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
