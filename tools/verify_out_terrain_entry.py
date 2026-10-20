#!/usr/bin/env python3
"""Verify a natural route onto tile $04 and its OUT-to-CAS handoff."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
ROUTE = TRACE / "out-route-to-04"
KEYS = (0x0B, 0x0B) + (0x08,) * 9


def checked_report(path: Path) -> dict:
    report = json.loads(path.read_text())
    require(report["timeout"] is None, f"trace stopped: {path}")
    item = report["snapshot"]
    require(describe(Path(item["path"])) ==
            {"size": item["size"], "sha256": item["sha256"]},
            f"snapshot differs: {path}")
    return report


def main() -> int:
    terrain_path = TRACE / "out-terrain-02" / "handoff.json"
    route_paths = [ROUTE / f"step-{number:02d}" / "handoff.json"
                   for number in range(1, len(KEYS) + 1)]
    enter_path = TRACE / "out-enter-04" / "handoff.json"
    cas_path = TRACE / "out-to-cas" / "handoff.json"
    if not all(path.is_file() for path in
               [terrain_path, *route_paths, enter_path, cas_path]):
        print("PENDING OUT terrain and CAS-entry trace")
        return 0
    first = checked_report(TRACE / "out-first-input" / "handoff.json")
    first_ram = main_ram(Path(first["snapshot"]["path"]))
    disk = first["working_game_disk"]

    terrain = checked_report(terrain_path)
    prior_down = checked_report(TRACE / "out-direction-0a" / "handoff.json")
    prior_down_ram = main_ram(Path(prior_down["snapshot"]["path"]))
    require(terrain["source_snapshot"] == prior_down["snapshot"] and
            terrain["working_game_disk"] == disk,
            "terrain-$02 replay ancestry differs")
    terrain_ram = main_ram(Path(terrain["snapshot"]["path"]))
    require(terrain["tile_lookup"] ==
            {"x": 39, "y": 35, "address": 0x6000 + 35 * 64 + 39,
             "raw": 4, "code": 2}, "terrain-$02 lookup differs")
    require((terrain_ram[0], terrain_ram[1]) == (39, 35),
            "terrain-$02 move did not commit")
    require(prior_down_ram[0x7EE5] == 0xC8 and terrain_ram[0x7EE5] == 0xC7 and
            terrain_ram[0x7EC6:0x7EC8] == prior_down_ram[0x7EC6:0x7EC8],
            "terrain-$02 food did not decrement")
    print("OUT terrain $02: ($27,$22) → ($27,$23); food decremented")

    source = first["snapshot"]
    for number, (key, path) in enumerate(zip(KEYS, route_paths), 1):
        report = checked_report(path)
        expected_xy = (39 - max(0, number - 2), 33 - min(2, number))
        expected_code = 4 if number == len(KEYS) else 1
        ram = main_ram(Path(report["snapshot"]["path"]))
        require(report["source_snapshot"] == source and
                report["working_game_disk"] == disk,
                f"route step {number} ancestry differs")
        require(report["input"] == {"key_ascii": key, "at_pc": "0x8A6C"},
                f"route step {number} key differs")
        require((ram[0], ram[1]) == expected_xy and
                report["tile_lookup"]["code"] == expected_code,
                f"route step {number} position/tile differs")
        address = 0x6000 + expected_xy[1] * 64 + expected_xy[0]
        require(report["tile_lookup"]["address"] == address and
                report["tile_lookup"]["raw"] == first_ram[address],
                f"route step {number} map byte differs")
        require(report["final_cpu"].startswith("pc=8A6C "),
                f"route step {number} did not return to outdoor input")
        source = report["snapshot"]
    print("OUT route: 11 moves reached ($1E,$1F), raw tile $08/code $04")

    enter = checked_report(enter_path)
    require(enter["source_snapshot"] == source and
            enter["working_game_disk"] == disk,
            "E entry did not descend from route")
    require(enter["input"] == {"key_ascii": 69, "at_pc": "0x8A6C"} and
            (enter["coords_before"], enter["coords_after"],
             enter["saved_coords_7E73"]) == ("1e1f", "1e1f", "1e1f"),
            "E input or coordinates differ")
    require([point["pc"] for point in enter["checkpoints"]] ==
            ["0x8A74", "0x89CB", "0x89CE", "0x89D0", "0x89DC",
             "0x90C8", "0x90D5", "0x90FF", "0x9137", "0x8EFA", "0x88FD"],
            "E-to-selector path differs")
    require(" a=04 " in enter["checkpoints"][6]["cpu"] and
            " a=10 " in enter["checkpoints"][8]["cpu"],
            "tile $04 did not select CAS offset $10")
    print("OUT E: tile $04 → selector A=$10, saved coordinate ($1E,$1F)")

    cas = checked_report(cas_path)
    require(cas["source_snapshot"] == enter["snapshot"] and
            cas["working_game_disk"] == disk,
            "CAS load did not descend from E selector")
    require([point["pc"] for point in cas["checkpoints"]] ==
            ["0x8920", "0x892B", "0x8956"] and
            cas["filename"] == "CAS" and cas["memory_match"] is True,
            "CAS loader path differs")
    expected = (ROOT / "extracted" / "CAS").read_bytes()
    cas_ram = main_ram(Path(cas["snapshot"]["path"]))
    require(cas["cas_bytes"] == len(expected) and
            cas_ram[0x8956:0x8956 + len(expected)] == expected,
            "CAS entry overlay differs from extracted file")
    print(f"CAS entry: {len(expected)} bytes match at $8956")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT terrain/entry verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
