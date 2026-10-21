#!/usr/bin/env python3
"""Check private four-key SPA replay against the byte-matched movement contract."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_spa_direction_controls import KEYS, OUTPUT
from verify_intro_support import main_ram


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING SPA four-direction runtime replay")
        return 0
    report = json.loads(path.read_text())
    source = report["source_snapshot"]
    disk = report["working_game_disk"]
    for item in (source, disk):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    expected_source = json.loads((ROOT / "build/traces/out-board-transitions/probe.json").read_text())["spa"]["snapshot"]
    require(source == expected_source, "SPA source snapshot lineage changed")
    ram = main_ram(Path(source["path"]))
    initial = {f"${address:04X}": ram[address] for address in
               (0x923E, 0x923F, 0x9240, 0x928A, 0x928B, 0x928E,
                0x7EE9, 0x7EEA, 0x7EEB, 0x7EEC)}
    require((initial["$923F"], initial["$9240"], initial["$928A"],
             initial["$928B"], initial["$7EE9"], initial["$7EEA"]) ==
            (3, 0, 0, 0, 0xE8, 0x03), "SPA source state differs")
    require(set(report["runs"]) == set(KEYS), "direction runs missing")
    for name, (key, handler, cost) in KEYS.items():
        run = report["runs"][name]
        require(run["key"] == key and run["handler"] == f"${handler:04X}" and
                run["cost"] == cost and run["initial"] == initial,
                f"{name}: dispatch or initial state differs")
        require([point["pc"] for point in run["checkpoints"]] ==
                [f"0x{address:04X}" for address in
                 (0x8A62, 0x8A6A, 0x8AB0, handler, 0xA154, 0xA1BA, 0x8A5F)],
                f"{name}: execution checkpoint differs")
        before, after = run["before_debit"], run["after_debit"]
        expected = {"up": (0xFE, 0, 3), "down": (2, 0, 3),
                    "right": (0, 0, 0), "left": (0, 0, 2)}[name]
        require((before["$928A"], before["$928B"], before["$923E"]) == expected,
                f"{name}: coordinate/turn staging differs")
        require(int.from_bytes(bytes((before["$7EE9"], before["$7EEA"])), "little") == 1000 and
                int.from_bytes(bytes((after["$7EE9"], after["$7EEA"])), "little") == 1000-cost and
                after["$7EEB"] == before["$7EEB"] and
                after["$7EEC"] == before["$7EEC"],
                f"{name}: fuel debit or shield differs")
        final = run["next_input"]
        require((final["$928A"], final["$928B"], final["$923F"],
                 final["$923E"], final["$7EE9"] + 256*final["$7EEA"]) ==
                {"up": (0xFE, 0, 3, 3, 995),
                 "down": (2, 0, 3, 3, 995),
                 "right": (0, 0, 0, 0, 998),
                 "left": (0, 0, 2, 2, 998)}[name],
                f"{name}: next-input state differs")
        require(run["final_cpu"].startswith("pc=8A5F"),
                f"{name}: did not return to SPA input")
    print("SPA direction movement, staged heading, and 5/2 Fuel debit verified")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SPA direction verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
