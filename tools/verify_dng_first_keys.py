#!/usr/bin/env python3
"""Check ordinary first dungeon keys W and Up against private snapshots."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
PATHS = (TRACE / "dng-first-input/handoff.json",
         TRACE / "dng-key-w/handoff.json",
         TRACE / "dng-key-up/handoff.json",
         TRACE / "dng-after-up/handoff.json")


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"dungeon key snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in PATHS):
        print("PENDING DNG first-key replays")
        return 0
    first, invalid, up, after = [json.loads(path.read_text()) for path in PATHS]
    require(all(item["timeout"] is None for item in (first, invalid, up, after)) and
            invalid["source_snapshot"] == up["source_snapshot"] == first["snapshot"] and
            after["source_snapshot"] == up["snapshot"] and
            all(item["working_game_disk"] == first["working_game_disk"]
                for item in (invalid, up, after)),
            "DNG key snapshot ancestry differs")
    disk = first["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG key game disk differs")
    original = checked_ram(first["snapshot"])
    invalid_ram = checked_ram(invalid["snapshot"])
    up_ram = checked_ram(up["snapshot"])
    after_ram = checked_ram(after["snapshot"])
    keys = original[0x7E53:0x7E6D]
    require(0x57 not in keys and 0x0B in keys and
            invalid["input"] == {"key_ascii": 87, "at_pc": "0x8DDA"} and
            [point["pc"] for point in invalid["checkpoints"]] ==
            ["0x8DE4", "0x8DD4", "0x8DD7", "0x8D99"] and
            " x=FF " in invalid["checkpoints"][2]["cpu"] and
            invalid["state_before"] == invalid["state_after"] and
            invalid_ram[0xA4E8:0xA4EA] == b"\x01\x01",
            "DNG W rejection differs")
    require(up["input"] == {"key_ascii": 11, "at_pc": "0x8DDA"} and
            [point["pc"] for point in up["checkpoints"]] ==
            ["0x8DE4", "0x8DD4", "0x8DD7", "0x8E0B", "0x8E95", "0x8E0E"] and
            up["patched_call"] == "20958e" and
            up["state_before"] == {"position": "0101", "facing": "0001",
                                   "hp": "9600", "food": "b400"} and
            up["state_after"] == {"position": "0102", "facing": "0001",
                                  "hp": "9600", "food": "b400"} and
            up_ram[0xA4E8:0xA4EA] == b"\x01\x02",
            "DNG Up handler or immediate move differs")
    require([point["pc"] for point in after["checkpoints"]] ==
            ["0x8DE6", "0x8DDA"] and
            after["state"] == up["state_after"] and
            after_ram[0xA4E8:0xA4EA] == b"\x01\x02",
            "DNG next key poll or state differs")
    print("DNG W absent from command table; lookup X=$FF, local position stays (1,1)")
    print("DNG Up → $8E95: local position (1,1)→(1,2); facing, HP, food stable to next poll")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG first-key verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
