#!/usr/bin/env python3
"""Check why one depth-one generated cell changes from $05 to $06."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_startup import cpu_pc
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
CASES = (
    ("initial", "out-to-dng", "dng-first-input", 0x8956, 0x40, 5),
    ("return1", "dng-stairs-k", "dng-level2-ascend", 0x8DDA, 0x6F, 6),
)


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"random-cell snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    paths = [TRACE / f"dng-random-tile-{label}/handoff.json"
             for label, *_ in CASES]
    if not all(path.is_file() for path in paths):
        print("PENDING first and returned depth-one random-cell traces")
        return 0
    for label, source_name, result_name, source_pc, random_byte, tile in CASES:
        report = json.loads((TRACE / f"dng-random-tile-{label}/handoff.json").read_text())
        source = json.loads((TRACE / source_name / "handoff.json").read_text())
        result = json.loads((TRACE / result_name / "handoff.json").read_text())
        disk = source["working_game_disk"]
        require(describe(Path(disk["path"])) ==
                {"size": disk["size"], "sha256": disk["sha256"]} and
                cpu_pc(source["final_cpu"]) == source_pc and
                report["timeout"] is None and
                report["source_snapshot"] == source["snapshot"] and
                report["working_game_disk"] == result["working_game_disk"] == disk and
                [point["pc"] for point in report["checkpoints"]] ==
                (["0x8DE4"] if source_pc == 0x8DDA else []) +
                ["0x8D23", "0x8D36", "0x8DDA"] and
                report["draw"] == {"random_byte": random_byte,
                                   "target_x": 2, "target_y": 3,
                                   "predicted_tile": tile, "depth": "01",
                                   "tile_after_loop": tile, "tile_at_poll": tile} and
                cpu_pc(report["final_cpu"]) == 0x8DDA and
                checked_ram(report["snapshot"]) == checked_ram(result["snapshot"]) and
                checked_ram(report["snapshot"])[0xB099 + 3*11 + 2] == tile,
                f"{label} random-cell draw, write, or independent RAM differs")
        print(f"{label}: random ${random_byte:02X} & 1 → tile ${tile:02X} at (2,3)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG random-cell verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
