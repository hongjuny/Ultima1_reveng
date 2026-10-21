#!/usr/bin/env python3
"""Check DNG template copy, seed, and the first generated 11×11 map."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "out-to-dng/handoff.json"
GENERATION = TRACE / "dng-generation/handoff.json"
FIRST = TRACE / "dng-first-input/handoff.json"


def checked_ram(item: dict) -> bytes:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG generation snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, GENERATION, FIRST)):
        print("PENDING DNG generation phases")
        return 0
    source, generation, first = [json.loads(path.read_text()) for path in
                                 (SOURCE, GENERATION, FIRST)]
    require(source["timeout"] is generation["timeout"] is first["timeout"] is None and
            generation["source_snapshot"] == first["source_snapshot"] == source["snapshot"] and
            generation["working_game_disk"] == first["working_game_disk"] ==
            source["working_game_disk"] and
            [point["pc"] for point in generation["checkpoints"]] ==
            ["0x8C5D", "0x8C87", "0x8CBB", "0x8DE6"],
            "DNG generator checkpoint ancestry differs")
    source_ram = checked_ram(source["snapshot"])
    generation_ram = checked_ram(generation["snapshot"])
    first_ram = checked_ram(first["snapshot"])
    original = (ROOT / "extracted/DNG").read_bytes()
    template = original[0xA619-0x8956:0xA692-0x8956]
    require(len(template) == 121 and
            generation["template_sha256"] == hashlib.sha256(template).hexdigest(),
            "DNG map template differs")
    phases = generation["phases"]
    require(len(phases) == 4 and
            [phase["pc"] for phase in phases] ==
            ["0x8C5D", "0x8C87", "0x8CBB", "0x8DE6"],
            "DNG generation phase list differs")
    maps = [bytes.fromhex(phase["map_hex"]) for phase in phases]
    require(all(len(grid) == 121 and
                hashlib.sha256(grid).hexdigest() == phase["map_sha256"]
                for grid, phase in zip(maps, phases)) and
            [phase["template_match"] for phase in phases] ==
            [False, True, False, False] and maps[1] == template and
            sum(a != b for a, b in zip(maps[1], maps[2])) == 35 and
            sum(a != b for a, b in zip(maps[2], maps[3])) == 10 and
            maps[3] == generation_ram[0xB099:0xB112] ==
            first_ram[0xB099:0xB112],
            "DNG template copy or generated map differs")
    seed_lo = ((source_ram[0x7EED] << 3) ^ source_ram[0x7E73] ^ 1) & 0xFF
    seed_hi = ((source_ram[0x7E74] << 2) ^ source_ram[0x7E6F]) & 0xFF
    require(phases[1]["seed_a504_a505"] == bytes((seed_lo, seed_hi)).hex() == "723c" and
            phases[1]["depth_a506"] == "01" and
            [phase["seed_a504_a505"] for phase in phases] ==
            ["0000", "723c", "a7c4", "0128"],
            "DNG generator seed or observed updates differ")
    print("DNG $A619 template (121 bytes) copied to $B099; 35 layout and 10 later cells changed")
    print("First seed: (($7EED<<3) XOR outdoor X XOR 1, (outdoor Y<<2) XOR $7E6F) = $72,$3C")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG generation verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
