#!/usr/bin/env python3
"""Descend to depth three while carrying the naturally accepted quest."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_dng_descend import direction_key, observe, route
from trace_dng_level2_to3 import play_key
from trace_dng_stairs_k import main as stair_k
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/odd-quest-dng-entry/poll/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-descend"


def require_quest(path: Path):
    item = json.loads(path.read_text())
    ram = main_ram(Path(item["snapshot"]["path"]))
    if list(ram[0x7EA9:0x7EB1]) != [0, 1, 0, 0, 0, 0, 0, 0]:
        raise RuntimeError(f"accepted quest lost at {path}")


def floor(source: Path, depth: int, max_actions: int = 80,
          previous_actions: list | None = None) -> Path:
    directory = OUTPUT / f"level-{depth}"
    directory.mkdir(parents=True, exist_ok=True)
    actions = [] if previous_actions is None else previous_actions
    for index in range(len(actions) + 1, max_actions + 1):
        prior = json.loads(source.read_text())
        position, facing, actual_depth, grid, hp = observe(prior)
        stairs = [(i % 11, i // 11) for i, value in enumerate(grid)
                  if value & 0x0F == 7]
        if actual_depth != depth or len(stairs) != 1 or hp <= 0:
            raise RuntimeError(f"unexpected dungeon floor state: {actual_depth}, {stairs}, HP {hp}")
        goal = stairs[0]
        if position == goal and grid[position[1] * 11 + position[0]] == 7:
            break
        path = route(grid, position, goal)
        key = 0x20 if path is None else direction_key(
            facing, (path[0][0] - position[0], path[0][1] - position[1]))
        destination = play_key(key, source, directory / f"action-{index:03d}")
        require_quest(destination)
        after = json.loads(destination.read_text())
        next_position, next_facing, next_depth, next_grid, next_hp = observe(after)
        actions.append({"number": index, "key": key, "before": list(position),
                        "facing_before": list(facing), "after": list(next_position),
                        "facing_after": list(next_facing), "hp_before": hp,
                        "hp_after": next_hp, "source_report": str(source),
                        "result_report": str(destination)})
        (directory / "route.json").write_text(json.dumps(actions, indent=2) + "\n")
        print(f"L{depth} {index:02d} ${key:02X} {position}→{next_position} "
              f"facing={next_facing} HP={next_hp}", flush=True)
        source = destination
    else:
        raise RuntimeError(f"floor {depth} stairs not reached in {max_actions} keys")
    print(f"level {depth} stair {goal} reached, facing={facing}, HP={hp}", flush=True)
    required = (0, 1) if depth == 1 else (0, -1)
    if facing != required:
        key = direction_key(facing, required)
        source = play_key(key, source, directory / "stairs-turn")
        require_quest(source)
        position, facing, actual_depth, grid, hp = observe(json.loads(source.read_text()))
        if position != goal or facing != required or actual_depth != depth:
            raise RuntimeError("stair turn lost position or depth")
    (directory / "stairs-source.json").write_text(
        json.dumps({"source_report": str(source)}, indent=2) + "\n")
    expected_facing = bytes((facing[0] & 255, facing[1] & 255)).hex()
    destination = directory / "descent"
    if stair_k(source, destination, expected_tile="07", expected_depth=f"{depth:02x}",
               branch="descend", expected_position=bytes(goal).hex(),
               expected_facing=expected_facing):
        raise RuntimeError(f"floor {depth} descent failed")
    result = destination / "handoff.json"
    require_quest(result)
    print(f"depth {depth}→{depth + 1} with accepted quest intact", flush=True)
    return result


def main(resume: bool = False):
    source = SOURCE
    require_quest(source)
    if resume:
        first_descent = OUTPUT / "level-1/descent/handoff.json"
        second_route = OUTPUT / "level-2/route.json"
        if not first_descent.is_file() or not second_route.is_file():
            raise RuntimeError("no second-floor route to resume")
        actions = json.loads(second_route.read_text())
        if not actions:
            raise RuntimeError("empty second-floor route")
        source = Path(actions[-1]["result_report"])
        require_quest(source)
        source = floor(source, 2, previous_actions=actions)
    else:
        for depth in (1, 2):
            source = floor(source, depth)
    position, facing, depth, grid, hp = observe(json.loads(source.read_text()))
    if depth != 3:
        raise RuntimeError(f"descent ended at depth {depth}")
    (OUTPUT / "route.json").write_text(json.dumps({
        "source_report": str(SOURCE), "result_report": str(source),
        "depth": depth, "position": list(position), "facing": list(facing),
        "hp": hp}, indent=2) + "\n")
    print(f"accepted quest at third floor: {position}, HP={hp}, report={source}")


if __name__ == "__main__":
    try:
        main(resume="--resume" in sys.argv)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest descent failed: {error}", file=sys.stderr)
        raise SystemExit(1)
