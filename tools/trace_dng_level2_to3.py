#!/usr/bin/env python3
"""Walk the generated second floor to its $07 stairs and enter level three."""

import contextlib
import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_dng_after_up import main as next_poll
from trace_dng_descend import direction_key, observe, route
from trace_dng_key_w import main as press_key
from trace_dng_level2_heavy_hit import main as trace_combat
from trace_dng_stairs_k import main as stair_k
from trace_startup import cpu_pc


SOURCE = ROOT / "build/traces/dng-stairs-k/handoff.json"
OUTPUT = ROOT / "build/traces/dng-level2-to3"
ENTRY = ROOT / "build/traces/dng-level3-entry"


def play_key(key: int, source: Path, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
        if press_key(key, output / "key", source, probe_move=key == 0x0B):
            raise RuntimeError(f"dungeon key failed; see {output / 'trace.log'}")
        if next_poll(output / "key/handoff.json", output / "poll"):
            raise RuntimeError(f"next poll failed; see {output / 'trace.log'}")
    return output / "poll/handoff.json"


def main(max_actions: int = 80) -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = SOURCE
    initial = json.loads(source.read_text())
    if initial["timeout"] is not None or cpu_pc(initial["final_cpu"]) != 0x8DDA:
        raise RuntimeError("source is not at level-two dungeon poll")
    position, facing, depth, grid, hp = observe(initial)
    goals = [(i % 11, i // 11) for i, value in enumerate(grid) if value == 7]
    if depth != 2 or goals != [(7, 3)]:
        raise RuntimeError(f"unexpected level-two stairs: depth={depth}, goals={goals}")
    goal = goals[0]
    actions = []
    for index in range(max_actions):
        prior = json.loads(source.read_text())
        if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
            raise RuntimeError(f"source is not at dungeon key poll: {source}")
        position, facing, depth, grid, hp = observe(prior)
        tile = grid[position[1] * 11 + position[0]]
        if depth != 2 or hp <= 0:
            raise RuntimeError(f"unexpected depth/HP: {depth}/{hp}")
        if position == goal and tile == 7:
            break
        path = route(grid, position, goal)
        if path is None:
            key = 0x20
        else:
            desired = (path[0][0] - position[0], path[0][1] - position[1])
            key = direction_key(facing, desired)
        source = play_key(key, source, OUTPUT / f"action-{index + 1:03d}")
        after = json.loads(source.read_text())
        after_position, after_facing, after_depth, after_grid, after_hp = observe(after)
        item = {"key": key, "before": list(position), "facing_before": list(facing),
                "tile_before": tile, "depth_before": depth, "hp_before": hp,
                "after": list(after_position), "facing_after": list(after_facing),
                "tile_after": after_grid[after_position[1] * 11 + after_position[0]],
                "depth_after": after_depth, "hp_after": after_hp,
                "key_report": str(OUTPUT / f"action-{index + 1:03d}/key/handoff.json"),
                "poll_report": str(source)}
        actions.append(item)
        (OUTPUT / "route.json").write_text(json.dumps(actions, indent=2) + "\n")
        print(f"{index + 1:02d} key=${key:02X} {position} {facing} → "
              f"{after_position} {after_facing} tile=${item['tile_after']:02X} HP={after_hp}",
              flush=True)
    else:
        raise RuntimeError(f"second-floor stair not reached in {max_actions} actions")
    print(f"second-floor stairs reached: {position}, facing {facing}, HP={hp}", flush=True)
    if facing[1] == 0:
        key = direction_key(facing, (0, -1))
        source = play_key(key, source, OUTPUT / "stairs-turn")
        ready = json.loads(source.read_text())
        position, facing, depth, grid, hp = observe(ready)
        if position != goal or facing[1] == 0 or grid[goal[1]*11 + goal[0]] != 7:
            raise RuntimeError("second-floor turn lost descending stair")
    (OUTPUT / "stairs-source.json").write_text(json.dumps({"source_report": str(source)}, indent=2) + "\n")
    expected_facing = bytes((facing[0] & 0xFF, facing[1] & 0xFF)).hex()
    if stair_k(source, ENTRY, expected_tile="07", expected_depth="02",
               branch="descend", expected_position="0703",
               expected_facing=expected_facing):
        raise RuntimeError("level-three descent K replay failed")
    for index in (1, 3, 4, 9):
        combat_output = (ROOT / "build/traces/dng-level2-heavy-hit" if index == 4 else
                         ROOT / f"build/traces/dng-level2-loss-{index:03d}")
        if trace_combat(OUTPUT / f"action-{index:03d}/key/handoff.json", combat_output):
            raise RuntimeError(f"level-two combat replay failed for action {index}")
    print("third-floor entry captured", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG level-two route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
