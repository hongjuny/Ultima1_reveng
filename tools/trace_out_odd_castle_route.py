#!/usr/bin/env python3
"""Walk the first world map to the castle whose quest index is one."""

from collections import deque
import contextlib
import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_out_direction import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/out-odd-castle-route"
GOAL = (22, 20)
KEYS = {(0, -1): 0x0B, (0, 1): 0x0A, (1, 0): 0x15, (-1, 0): 0x08}
PASSABLE = {2, 4, 8}


def shortest(grid, start, goal):
    queue = deque([start])
    previous = {start: None}
    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            path = []
            point = goal
            while point != start:
                path.append(point)
                point = previous[point]
            return path[::-1]
        for dx, dy in KEYS:
            dest = (x + dx, y + dy)
            if (dest in previous or not 0 <= dest[0] < 64 or
                    not 0 <= dest[1] < 64 or
                    grid[dest[1] * 64 + dest[0]] not in PASSABLE):
                continue
            previous[dest] = (x, y)
            queue.append(dest)
    raise RuntimeError(f"no walking route to {goal}")


def main(source_report: Path = SOURCE, output: Path = OUTPUT,
         expected_start: tuple[int, int] = (39, 33),
         required_quest: int | None = None):
    initial = json.loads(source_report.read_text())
    if initial["timeout"] is not None or cpu_pc(initial["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source is not at OUT input")
    ram = main_ram(Path(initial["snapshot"]["path"]))
    start = tuple(ram[:2])
    grid = ram[0x6000:0x7000]
    if start != expected_start or grid[GOAL[1] * 64 + GOAL[0]] != 8:
        raise RuntimeError("source location or destination castle differs")
    path = shortest(grid, start, GOAL)
    output.mkdir(parents=True, exist_ok=True)
    source = source_report
    entries = []
    current = start
    for number, dest in enumerate(path, 1):
        key = KEYS[(dest[0] - current[0], dest[1] - current[1])]
        action = output / f"step-{number:02d}"
        action.mkdir(parents=True, exist_ok=True)
        with (action / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
            if replay(key, source, action):
                raise RuntimeError(f"step {number} failed; see {action / 'trace.log'}")
        report_path = action / "handoff.json"
        report = json.loads(report_path.read_text())
        reached = main_ram(Path(report["snapshot"]["path"]))
        actual = tuple(reached[:2])
        if cpu_pc(report["final_cpu"]) != 0x8A6C or actual != dest:
            raise RuntimeError(f"step {number}: expected {dest}, got {actual}")
        if required_quest is not None and reached[0x7EAA] != required_quest:
            raise RuntimeError(f"quest changed at step {number}")
        expected_code = grid[dest[1] * 64 + dest[0]] >> 1
        if report["tile_lookup"]["code"] != expected_code:
            raise RuntimeError(f"step {number}: map tile changed")
        item = {"number": number, "key": key, "before": list(current),
                "after": list(actual), "tile_code": expected_code,
                "source_report": str(source), "result_report": str(report_path)}
        entries.append(item)
        (output / "route.json").write_text(json.dumps(entries, indent=2) + "\n")
        print(f"{number:02d}/{len(path)} key=${key:02X} {current}→{actual} "
              f"tile=${expected_code:02X}", flush=True)
        source = report_path
        current = actual
    print(f"odd-quest castle reached at {current}; report {source}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd-quest castle route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
