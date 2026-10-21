#!/usr/bin/env python3
"""Replay the shortest mapped land route from the castle to a dungeon tile."""

from collections import deque
import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_out_direction import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


TRACE = ROOT / "build" / "traces"
SOURCE = TRACE / "out-route-to-04" / "step-11" / "handoff.json"
OUTPUT = TRACE / "out-route-to-07"
DIRECTIONS = ((0, -1, 0x0B), (0, 1, 0x0A), (-1, 0, 0x08), (1, 0, 0x15))


def route(ram: bytes, start: tuple[int, int]):
    grid = ram[0x6000:0x7000]
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        (x, y), path = queue.popleft()
        if grid[y * 64 + x] >> 1 == 7:
            return path
        for dx, dy, key in DIRECTIONS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < 64 and 0 <= ny < 64 and (nx, ny) not in visited:
                code = grid[ny * 64 + nx] >> 1
                if code in (1, 2, 4, 5, 6, 7):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(key, (nx, ny), code)]))
    raise RuntimeError("no mapped land route to code-$07 tile")


def main() -> int:
    source = SOURCE
    prior = json.loads(source.read_text())
    ram = main_ram(Path(prior["snapshot"]["path"]))
    steps = route(ram, (ram[0], ram[1]))
    print(f"mapped route: {len(steps)} steps to {steps[-1][1]}", flush=True)
    for index, (key, position, code) in enumerate(steps, 1):
        target = OUTPUT / f"step-{index:02d}"
        if replay(key, source, target):
            return 1
        report = json.loads((target / "handoff.json").read_text())
        current = main_ram(Path(report["snapshot"]["path"]))
        actual = (current[0], current[1])
        if cpu_pc(report["final_cpu"]) != 0x8A6C or actual != position or \
                report["tile_lookup"]["code"] != code:
            raise RuntimeError(f"step {index}: expected {position} code {code}; got "
                               f"{actual} code {report['tile_lookup']['code']}")
        print(f"route step {index}/{len(steps)}: {actual} code ${code:02X}", flush=True)
        source = target / "handoff.json"
    (OUTPUT / "route.json").write_text(json.dumps({
        "source": str(SOURCE), "steps": len(steps), "end_report": str(source),
        "end_position": steps[-1][1], "end_code": 7,
    }, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT dungeon route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
