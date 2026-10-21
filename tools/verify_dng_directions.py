#!/usr/bin/env python3
"""Check first DNG direction keys and open/wall forward branches."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
INITIAL = TRACE / "dng-first-input/handoff.json"
CASES = (
    ("up", 0x0B, "20958e", "0102", "0001"),
    ("down", 0x0A, "20488e", "0101", "00ff"),
    ("right", 0x15, "205b8e", "0101", "ff00"),
    ("left", 0x08, "20788e", "0101", "0100"),
    ("space", 0x20, "208c8f", "0101", "0001"),
)


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"dungeon snapshot differs: {path}")
    return main_ram(path)


def report(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    paths = [INITIAL]
    for label, *_ in CASES:
        paths += [TRACE / f"dng-key-{label}/handoff.json",
                  TRACE / f"dng-after-{label}/handoff.json"]
    for label in ("west-wall", "east-open"):
        paths += [TRACE / f"dng-forward-{label}/handoff.json",
                  TRACE / f"dng-after-{label}/handoff.json"]
    if not all(path.is_file() for path in paths):
        print("PENDING DNG direction and wall replays")
        return 0
    initial = report(INITIAL)
    original = checked_ram(initial["snapshot"])
    grid = original[0xB099:0xB112]
    require(len(grid) == 121 and
            all(grid[x] == grid[110 + x] == 1 for x in range(11)) and
            all(grid[y*11] == grid[y*11 + 10] == 1 for y in range(11)) and
            grid[1*11 + 1] == 8 and grid[2*11 + 1] == 0 and
            grid[1*11 + 0] == 1 and grid[1*11 + 2] == 0,
            "first generated DNG 11×11 map differs")
    disk = initial["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG game disk differs")
    for label, key, patched, position, facing in CASES:
        key_report = report(TRACE / f"dng-key-{label}/handoff.json")
        next_report = report(TRACE / f"dng-after-{label}/handoff.json")
        require(key_report["timeout"] is None and next_report["timeout"] is None and
                key_report["source_snapshot"] == initial["snapshot"] and
                next_report["source_snapshot"] == key_report["snapshot"] and
                key_report["working_game_disk"] == next_report["working_game_disk"] == disk and
                key_report["input"] == {"key_ascii": key, "at_pc": "0x8DDA"} and
                key_report["patched_call"] == patched and
                [point["pc"] for point in key_report["checkpoints"]] ==
                ["0x8DE4", "0x8DD4", "0x8DD7", "0x8E0B",
                 "0x" + patched[4:6].upper() + patched[2:4].upper(), "0x8E0E"] and
                key_report["state_before"] ==
                {"position": "0101", "facing": "0001", "hp": "9600", "food": "b400"} and
                key_report["state_after"] == next_report["state"] ==
                {"position": position, "facing": facing,
                 "hp": "9600", "food": "b400"} and
                [point["pc"] for point in next_report["checkpoints"]] ==
                ["0x8DE6", "0x8DDA"],
                f"DNG {label} direction or next-poll state differs")
        checked_ram(key_report["snapshot"])
        checked_ram(next_report["snapshot"])
    for label, source, tile, branch, position, facing in (
            ("west-wall", "right", 1, "0x8EA7", "0101", "ff00"),
            ("east-open", "left", 0, "0x8EBE", "0201", "0100")):
        prior = report(TRACE / f"dng-after-{source}/handoff.json")
        forward = report(TRACE / f"dng-forward-{label}/handoff.json")
        next_report = report(TRACE / f"dng-after-{label}/handoff.json")
        require(forward["timeout"] is None and next_report["timeout"] is None and
                forward["source_snapshot"] == prior["snapshot"] and
                next_report["source_snapshot"] == forward["snapshot"] and
                forward["working_game_disk"] == next_report["working_game_disk"] == disk and
                forward["input"] == {"key_ascii": 11, "at_pc": "0x8DDA"} and
                forward["patched_call"] == "20958e" and
                [point["pc"] for point in forward["checkpoints"]] ==
                ["0x8DE4", "0x8DD4", "0x8DD7", "0x8E0B", "0x8E95",
                 "0x8E9B", branch, "0x8E0E"] and
                f" a={tile:02X} " in forward["checkpoints"][5]["cpu"] and
                forward["state_after"] == next_report["state"] ==
                {"position": position, "facing": facing,
                 "hp": "9600", "food": "b400"} and
                [point["pc"] for point in next_report["checkpoints"]] ==
                ["0x8DE6", "0x8DDA"],
                f"DNG {label} tile or movement branch differs")
        checked_ram(forward["snapshot"])
        checked_ram(next_report["snapshot"])
    print("DNG 11×11 map at $B099: first border $01, interior (2,1)=$00")
    print("Down/Right/Left turn facing; Up advances; Space stays; no HP/food change")
    print("Forward west into $01 → $8EA7 blocked; east into $00 → $8EBE, (1,1)→(2,1)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG direction verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
