#!/usr/bin/env python3
"""Check private outdoor route, code-$07 dispatch, DNG load and first poll."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_out_route_to_07 import OUTPUT, SOURCE, route
from verify_intro_support import main_ram, require


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    enter_path = ROOT / "build/traces/out-enter-07/handoff.json"
    load_path = ROOT / "build/traces/out-to-dng/handoff.json"
    first_path = ROOT / "build/traces/dng-first-input/handoff.json"
    if not all(path.is_file() for path in (SOURCE, OUTPUT / "route.json",
                                           enter_path, load_path, first_path)):
        print("PENDING OUT-to-DNG route and first-input trace")
        return 0
    start = json.loads(SOURCE.read_text())
    start_ram = checked_ram(start["snapshot"])
    steps = route(start_ram, (start_ram[0], start_ram[1]))
    route_record = json.loads((OUTPUT / "route.json").read_text())
    require(len(steps) == route_record["steps"] == 29 and
            steps[-1][1] == (43, 15) and route_record["end_code"] == 7,
            "dungeon route definition differs")
    previous = start
    for index, (key, position, code) in enumerate(steps, 1):
        path = OUTPUT / f"step-{index:02d}" / "handoff.json"
        require(path.is_file(), f"missing dungeon route step {index}")
        report = json.loads(path.read_text())
        require(report["timeout"] is None and
                report["source_snapshot"] == previous["snapshot"] and
                report["working_game_disk"] == start["working_game_disk"] and
                report["input"]["key_ascii"] == key,
                f"dungeon route ancestry/input differs at step {index}")
        ram = checked_ram(report["snapshot"])
        require((ram[0], ram[1]) == position and
                report["tile_lookup"]["code"] == code and
                report["tile_lookup"]["raw"] == start_ram[0x6000 + position[1]*64 + position[0]],
                f"dungeon route tile differs at step {index}")
        previous = report
    enter, load, first = [json.loads(path.read_text()) for path in
                          (enter_path, load_path, first_path)]
    require(all(report["timeout"] is None for report in (enter, load, first)) and
            enter["source_snapshot"] == previous["snapshot"] and
            load["source_snapshot"] == enter["snapshot"] and
            first["source_snapshot"] == load["snapshot"] and
            all(report["working_game_disk"] == start["working_game_disk"]
                for report in (enter, load, first)),
            "dungeon entry ancestry differs")
    disk = start["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "dungeon route game disk differs")
    require(enter["coords_before"] == enter["saved_coords_7E73"] == "2b0f" and
            [point["pc"] for point in enter["checkpoints"]] ==
            ["0x8A74", "0x89CB", "0x89CE", "0x89D0", "0x89DC", "0x90C8",
             "0x90D5", "0x90FF", "0x9137", "0x8EFA", "0x88FD"] and
            " a=08 " in enter["final_cpu"],
            "dungeon E dispatch differs")
    require(load["filename"] == "DNG" and load["memory_match"] is True and
            load["dng_bytes"] == len((ROOT / "extracted/DNG").read_bytes()) and
            [point["pc"] for point in load["checkpoints"]] ==
            ["0x8920", "0x892B", "0x8956"],
            "DNG overlay load differs")
    require([point["pc"] for point in first["checkpoints"]] ==
            ["0x8C5D", "0x8DE6", "0x8982", "0x8DDA"] and
            first["final_cpu"].startswith("pc=8DDA "),
            "DNG first input differs")
    ram = checked_ram(first["snapshot"])
    require(ram[0:2] == ram[0x7E73:0x7E75] == bytes((43, 15)) and
            ram[0xA4E8:0xA4EA] == b"\x01\x01" and
            ram[0xB099:0xB112].hex() == first["generated_map_prefix"] and
            len(first["generated_map_prefix"]) == 242,
            "DNG first-input state or generated map differs")
    print("OUT tile $07 at (43,15) → selector $08 → DNG, all 10051 bytes match")
    print("DNG generator reached $8C5D; first key read $8DDA; 121-byte map area checked")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"OUT-to-DNG verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
