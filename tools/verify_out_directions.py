#!/usr/bin/env python3
"""Check four independent outdoor direction replays and their coordinate deltas."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
KEYS = (0x0B, 0x0A, 0x15, 0x08)
HANDLERS = (0x9357, 0x935D, 0x9363, 0x9369)
EXPECTED_COORDS = ((0x27, 0x20), (0x27, 0x22), (0x28, 0x21), (0x26, 0x21))
CHECKPOINTS = ("0x8A74", "0x89CB", "0x89CE", "0x89D0", "0x89DC",
               None, "0x99D1", "0x99F6", "0x89DF", "0x8995", "0x89A1", "0x8A6C")


def main() -> int:
    paths = [TRACE / f"out-direction-{key:02x}" / "handoff.json" for key in KEYS]
    if not all(path.is_file() for path in paths):
        print("PENDING OUT four-direction replay")
        return 0
    origin = json.loads((TRACE / "out-first-input" / "handoff.json").read_text())
    before = main_ram(Path(origin["snapshot"]["path"]))
    require((before[0], before[1]) == (0x27, 0x21), "source coordinates differ")
    for index, (key, handler, coords, path) in enumerate(
            zip(KEYS, HANDLERS, EXPECTED_COORDS, paths)):
        report = json.loads(path.read_text())
        require(report["timeout"] is None, f"${key:02X} replay stopped")
        require(report["source_snapshot"] == origin["snapshot"] and
                report["working_game_disk"] == origin["working_game_disk"],
                f"${key:02X} did not use the shared origin")
        require(report["input"] == {"key_ascii": key, "at_pc": "0x8A6C"},
                f"${key:02X} input differs")
        require(report["command_index"] == index * 2 and
                report["handler"] == handler, f"${key:02X} dispatch differs")
        actual_points = [point["pc"] for point in report["checkpoints"]]
        expected_points = list(CHECKPOINTS)
        expected_points[5] = f"0x{handler:04X}"
        require(actual_points == expected_points, f"${key:02X} path differs")
        item = report["snapshot"]
        snapshot = Path(item["path"])
        require(describe(snapshot) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"${key:02X} snapshot hash differs")
        after = main_ram(snapshot)
        lookup = report["tile_lookup"]
        address = 0x6000 + coords[1] * 64 + coords[0]
        require(lookup == {"x": coords[0], "y": coords[1],
                           "address": address, "raw": before[address],
                           "code": before[address] >> 1},
                f"${key:02X} tile lookup differs from map")
        require((after[0], after[1]) == coords,
                f"${key:02X} resulting coordinates differ")
        require((after[0x7EE4], after[0x7EDB]) == (0x45, 0x01),
                f"${key:02X} resource/time values differ")
        require((after[0x7EC6:0x7EC8], after[0x7EE5:0x7EE7]) ==
                (before[0x7EC6:0x7EC8], before[0x7EE5:0x7EE7]),
                f"${key:02X} health or food changed")
        print(f"OUT ${key:02X}: ${handler:04X}, "
              f"($27,$21) → (${coords[0]:02X},${coords[1]:02X}), "
              "$7EE4=$45, $7EDB=$01")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT direction verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
