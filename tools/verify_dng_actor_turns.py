#!/usr/bin/env python3
"""Reconstruct every level-two route map from descending actor-slot moves."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces/dng-level2-to3"
MAP = 0xB099


def checked_ram(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG actor-turn snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    reports = [TRACE / f"action-{index:03d}/poll/handoff.json"
               for index in range(1, 12)]
    if not all(path.is_file() for path in reports):
        print("PENDING DNG level-two actor-turn snapshots")
        return 0
    moves = 0
    grids = {}
    for index, path in enumerate(reports, 1):
        report = json.loads(path.read_text())
        require(report["timeout"] is None, f"DNG turn {index} timed out")
        before = checked_ram(report["source_snapshot"])
        after = checked_ram(report["snapshot"])
        require(before[0xA506] == after[0xA506] == 2,
                f"DNG turn {index} changed level")
        grid = bytearray(before[MAP:MAP + 121])
        for slot in range(5, 0, -1):
            old_x, old_y = before[0xA50E + slot], before[0xA514 + slot]
            new_x, new_y = after[0xA50E + slot], after[0xA514 + slot]
            if (old_x, old_y) == (new_x, new_y):
                continue
            require(before[0xA508 + slot] == after[0xA508 + slot] == 0 and
                    0 <= min(old_x, old_y, new_x, new_y) and
                    max(old_x, old_y, new_x, new_y) < 11 and
                    abs(new_x - old_x) + abs(new_y - old_y) == 1,
                    f"DNG turn {index} slot {slot} move is not one active step")
            old_index, new_index = old_y * 11 + old_x, new_y * 11 + new_x
            require(grid[old_index] >> 4 == slot,
                    f"DNG turn {index} slot {slot} old map occupancy differs")
            grid[old_index] &= 0x0F
            require(grid[new_index] >> 4 == 0,
                    f"DNG turn {index} slot {slot} destination occupied")
            grid[new_index] |= slot << 4
            moves += 1
        require(grid == after[MAP:MAP + 121],
                f"DNG turn {index} reconstructed map differs")
        grids[index] = bytes(grid)
    stair = 7 * 11 + 3
    require((grids[2][stair], grids[3][stair], grids[5][stair]) ==
            (0x58, 0x48, 0x08),
            "DNG entrance tile overlay sequence differs")
    require(moves == 22, f"DNG observed actor-move count differs: {moves}")
    print("DNG 11 level-two turns: 22 slot moves reproduce every 121-byte map")
    print("Entrance (3,7) retains $08 under slot 5, then slot 4, then neither: $58→$48→$08")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG actor-turn verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
