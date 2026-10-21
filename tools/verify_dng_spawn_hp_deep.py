#!/usr/bin/env python3
"""Check level-two and level-three actor HP random factors."""

import json
from pathlib import Path
import re
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
CASES = (
    ("level2", "dng-descend/stairs-turn/poll", (1, 4, 5),
     (0xF2, 0x20, 0x1B), (2, 0, 3), (12, 10, 25)),
    ("level3", "dng-level2-to3/action-011/poll", (1, 5, 4),
     (0xB3, 0xD3, 0x2C), (8, 4, 8), (18, 30, 42)),
)


def checked_ram(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG spawn HP snapshot differs: {path}")
    return main_ram(path)


def accumulator(cpu):
    match = re.search(r"\ba=([0-9A-F]{2})\b", cpu)
    require(match is not None, f"DNG spawn HP CPU register missing: {cpu}")
    return int(match.group(1), 16)


def main() -> int:
    reports = [(TRACE / source / "handoff.json",
                TRACE / f"dng-spawn-hp-{label}/handoff.json",
                TRACE / f"dng-generation-{label}/handoff.json")
               for label, source, *_ in CASES]
    if not all(path.is_file() for group in reports for path in group):
        print("PENDING DNG deeper-floor spawn HP traces")
        return 0
    for ((label, _, slots, raw, factors, hp),
         (source_path, hp_path, generation_path)) in zip(CASES, reports):
        source, trace, generation = [json.loads(path.read_text()) for path in
                                     (source_path, hp_path, generation_path)]
        require(all(item["timeout"] is None for item in
                    (source, trace, generation)) and
                trace["source_snapshot"] == generation["source_snapshot"] ==
                source["snapshot"] and
                trace["working_game_disk"] == generation["working_game_disk"] ==
                source["working_game_disk"],
                f"DNG {label} HP trace ancestry differs")
        disk = source["working_game_disk"]
        require(describe(Path(disk["path"])) ==
                {"size": disk["size"], "sha256": disk["sha256"]},
                f"DNG {label} game disk differs")
        final_ram = checked_ram(trace["snapshot"])
        require(final_ram == checked_ram(generation["snapshot"]),
                f"DNG {label} HP trace differs from independent generation")
        points = trace["checkpoints"]
        require(len(points) == 12 and
                [item["pc"] for item in points] ==
                [pc for _ in range(3) for pc in
                 ("0x9C3C", "0x8259", "0x9C3F", "0x9C54")],
                f"DNG {label} HP checkpoints differ")
        depth = 2 if label == "level2" else 3
        coefficient = 4 if depth == 2 else 9
        require(final_ram[0xA506] == depth and
                final_ram[0xA60D + depth] == coefficient and
                final_ram[0xA60D:0xA619] ==
                bytes(value * value for value in range(12)),
                f"DNG {label} coefficient differs")
        for index, slot in enumerate(slots):
            call, draw, result, stored = points[4 * index:4 * index + 4]
            factor = factors[index]
            require(all(item["slot"] == slot and item["depth"] == depth and
                        item["coefficient"] == coefficient for item in
                        (call, draw, result, stored)) and
                    accumulator(call["cpu"]) == coefficient and
                    accumulator(draw["cpu"]) == raw[index] and
                    accumulator(result["cpu"]) == factor == raw[index] % coefficient and
                    draw["random_bound_69"] == coefficient and
                    result["random_bound_69"] == factor and
                    call["base_hp_a4f2_a4f3"] == "0a00" and
                    stored["slot_hp"] == hp[index] == 10 + slot * factor and
                    final_ram[0xA51A + slot] +
                    256 * final_ram[0xA520 + slot] == hp[index],
                    f"DNG {label} slot {slot} HP calculation differs")
        print(f"DNG {label}: slots {slots}, draws {[hex(x) for x in raw]}, "
              f"factors {factors}, HP {hp}; independent RAM matched")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG deeper spawn HP verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
