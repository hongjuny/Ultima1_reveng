#!/usr/bin/env python3
"""Check template copy, seed, and stair placement across observed floors."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_startup import cpu_pc
from verify_dng_stairs import checked_ram
from verify_intro_support import require


TRACE = ROOT / "build/traces"
CASES = (
    ("level2", "dng-descend/stairs-turn/poll", "dng-stairs-k", 2,
     "713c", "4731", "a59b", (7, 3), (3, 7)),
    ("level3", "dng-level2-to3/action-011/poll", "dng-level3-entry", 3,
     "703c", "a6e5", "e568", (3, 7), (7, 3)),
    ("return1", "dng-stairs-k", "dng-level2-ascend", 1,
     "723c", "a7c4", "0128", (3, 7), (1, 1)),
)
PCS = ("0x8C5D", "0x8C87", "0x8CBB", "0x8DE6", "0x8DDA")


def main() -> int:
    paths = [TRACE / f"dng-generation-{label}/handoff.json"
             for label, *_ in CASES]
    if not all(path.is_file() for path in paths):
        print("PENDING DNG multi-level generator traces")
        return 0
    source_file = (ROOT / "extracted/DNG").read_bytes()
    template = source_file[0xA619-0x8956:0xA692-0x8956]
    require(len(template) == 121, "dungeon template length differs")
    for label, source_name, result_name, depth, seed, layout_seed, final_seed, down, up in CASES:
        report = json.loads((TRACE / f"dng-generation-{label}/handoff.json").read_text())
        source = json.loads((TRACE / source_name / "handoff.json").read_text())
        result = json.loads((TRACE / result_name / "handoff.json").read_text())
        disk = source["working_game_disk"]
        require(describe(Path(disk["path"])) ==
                {"size": disk["size"], "sha256": disk["sha256"]} and
                report["timeout"] is None and
                report["source_snapshot"] == source["snapshot"] and
                report["working_game_disk"] == result["working_game_disk"] == disk and
                report["template_sha256"] == hashlib.sha256(template).hexdigest() and
                [point["pc"] for point in report["checkpoints"]] ==
                ["0x8DE4", *PCS] and
                cpu_pc(report["final_cpu"]) == 0x8DDA,
                f"{label} generator ancestry or checkpoints differ")
        phases = report["phases"]
        require([phase["pc"] for phase in phases] == list(PCS) and
                [phase["depth"] for phase in phases] == [f"{depth:02x}"] * 5 and
                [phase["seed"] for phase in phases[1:]] ==
                [seed, layout_seed, final_seed, final_seed],
                f"{label} depth or seed stages differ")
        for phase in phases:
            grid = bytes.fromhex(phase["map_hex"])
            require(len(grid) == 121 and
                    hashlib.sha256(grid).hexdigest() == phase["map_sha256"] and
                    phase["template_match"] == (grid == template),
                    f"{label} stage {phase['label']} map differs")
        require(bytes.fromhex(phases[1]["map_hex"]) == template and
                phases[3]["map_hex"] == phases[4]["map_hex"] and
                phases[1]["map_hex"] != phases[2]["map_hex"],
                f"{label} template, layout, or post-loop state differs")
        final_grid = bytes.fromhex(phases[-1]["map_hex"])
        require(final_grid[down[1] * 11 + down[0]] == 7 and
                final_grid[up[1] * 11 + up[0]] == 8 and
                (depth != 1 or final_grid[3*11 + 7] == 0),
                f"{label} stair placement differs")
        before = checked_ram(source["snapshot"])
        actual = checked_ram(report["snapshot"])
        independent = checked_ram(result["snapshot"])
        expected_seed = bytes((((before[0x7EED] << 3) ^ before[0x7E73] ^ depth) & 255,
                               ((before[0x7E74] << 2) ^ before[0x7E6F]) & 255)).hex()
        require(expected_seed == seed and actual == independent and
                actual[0xB099:0xB112] == final_grid and actual[0xA506] == depth,
                f"{label} seed formula or independent full RAM differs")
        print(f"{label}: seed {seed} → {layout_seed} → {final_seed}; "
              f"$07 at {down}, $08 at {up}; independent RAM matched")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG level generation verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
