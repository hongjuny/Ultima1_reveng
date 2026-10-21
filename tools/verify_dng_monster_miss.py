#!/usr/bin/env python3
"""Check the one-byte RNG intervention that selects a dungeon miss."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_cas_guard_miss import next_random
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-east-to-03-step-1/handoff.json"
HIT = TRACE / "dng-monster-turn/handoff.json"
MISS = TRACE / "dng-monster-miss/handoff.json"


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"dungeon miss snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, HIT, MISS)):
        print("PENDING controlled DNG monster miss")
        return 0
    source, hit, miss = [json.loads(path.read_text()) for path in (SOURCE, HIT, MISS)]
    require(source["timeout"] is hit["timeout"] is miss["timeout"] is None and
            hit["source_snapshot"] == miss["source_snapshot"] == source["snapshot"] and
            hit["working_game_disk"] == miss["working_game_disk"] ==
            source["working_game_disk"] and
            miss["intervention_snapshots"] is not None and
            [point["pc"] for point in miss["checkpoints"]] ==
            ["0x9A5C", "0x9A64", "0x8DDA"],
            "DNG controlled miss ancestry or branch differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG miss game disk differs")
    checked_ram(source["snapshot"])
    before = checked_ram(miss["intervention_snapshots"]["before"])
    after = checked_ram(miss["intervention_snapshots"]["after"])
    intervention = miss["controlled_change"]
    require([(i, a, b) for i, (a, b) in enumerate(zip(before, after)) if a != b] ==
            [(0x1E27, 0xF5, 0x22)] and
            intervention == {"address": "0x1E27", "before": 0xF5,
                             "after": 0x22, "original_roll": 0xA6,
                             "predicted_roll": 0x00, "threshold": 0x45} and
            next_random(before[0x1E18:0x1E28]) == 0xA6 and
            next_random(after[0x1E18:0x1E28]) == 0x00,
            "DNG one-byte RNG intervention or predictions differ")
    hit_ram, miss_ram = checked_ram(hit["snapshot"]), checked_ram(miss["snapshot"])
    require(miss["before_hp"] == miss["after_hp"] == "9600" and
            miss["position"] == "0301" and
            hit_ram[0x7EC6:0x7EC8] == b"\x94\x00" and
            miss_ram[0x7EC6:0x7EC8] == b"\x96\x00" and
            miss_ram[0xA4E8:0xA4EA] == b"\x03\x01" and
            miss_ram[0xB099:0xB112] == hit_ram[0xB099:0xB112],
            "DNG miss outcome or map differs")
    print("controlled DNG miss: RNG byte $1E27 $F5→$22, hit roll $A6→$00 (<$45)")
    print("HP stays $0096 versus ordinary-hit $0094; position and 11×11 map match")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG controlled miss verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
