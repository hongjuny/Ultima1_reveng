#!/usr/bin/env python3
"""Walk the first dungeon to its $07 stairs and replay both K transitions.

All snapshots and the generated map remain under ignored build/traces.
The route is recalculated after each key because dungeon occupants move.
"""

from collections import deque
import contextlib
import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_dng_after_up import main as next_poll
from trace_dng_key_w import main as press_key
from trace_dng_stairs_k import main as stair_k
from trace_startup import cpu_pc
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/dng-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/dng-descend"
GOAL = (3, 7)
DELTAS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def signed(value: int) -> int:
    return value - 256 if value >= 128 else value


def observe(report: dict) -> tuple[tuple[int, int], tuple[int, int], int, bytes, int]:
    item = report["snapshot"]
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"snapshot changed: {path}")
    ram = main_ram(path)
    position = tuple(ram[0xA4E8:0xA4EA])
    facing = tuple(signed(v) for v in ram[0xA4EC:0xA4EE])
    if not all(0 <= v < 11 for v in position):
        raise RuntimeError(f"invalid dungeon position: {position}")
    return position, facing, ram[0xA506], ram[0xB099:0xB112], int.from_bytes(ram[0x7EC6:0x7EC8], "little")


def route(grid: bytes, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    queue = deque([start])
    parents = {start: None}
    while queue:
        x, y = queue.popleft()
        if (x, y) == goal:
            path = []
            point = goal
            while point != start:
                path.append(point)
                point = parents[point]
            return path[::-1]
        for dx, dy in DELTAS:
            dest = x + dx, y + dy
            nx, ny = dest
            if not (0 <= nx < 11 and 0 <= ny < 11) or dest in parents:
                continue
            tile = grid[ny * 11 + nx]
            if tile in (1, 3) or tile >= 10:
                continue
            parents[dest] = (x, y)
            queue.append(dest)
    return None


def direction_key(facing: tuple[int, int], desired: tuple[int, int]) -> int:
    if desired == facing:
        return 0x0B  # forward
    if desired == (-facing[0], -facing[1]):
        return 0x0A  # turn around
    if desired == (-facing[1], facing[0]):
        return 0x15  # right
    if desired == (facing[1], -facing[0]):
        return 0x08  # left
    raise RuntimeError(f"cannot turn {facing} to {desired}")


def main(max_actions: int = 80) -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = SOURCE
    history = []
    for index in range(max_actions):
        prior = json.loads(source.read_text())
        if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
            raise RuntimeError(f"source is not at dungeon key poll: {source}")
        position, facing, depth, grid, hp = observe(prior)
        tile = grid[position[1] * 11 + position[0]]
        if depth != 1 or hp <= 0:
            raise RuntimeError(f"unexpected depth/HP: {depth}/{hp}")
        if position == GOAL and tile == 7:
            print(f"stairs reached: {position}, tile=${tile:02X}, depth={depth}, HP={hp}", flush=True)
            break
        path = route(grid, position, GOAL)
        if path is None:
            key = 0x20  # wait for a blocking actor to move
        else:
            desired = (path[0][0] - position[0], path[0][1] - position[1])
            key = direction_key(facing, desired)
        action = OUTPUT / f"action-{index + 1:03d}"
        action.mkdir(exist_ok=True)
        with (action / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
            if press_key(key, action / "key", source, probe_move=key == 0x0B):
                raise RuntimeError(f"dungeon key failed; see {action / 'trace.log'}")
            if next_poll(action / "key/handoff.json", action / "poll"):
                raise RuntimeError(f"next poll failed; see {action / 'trace.log'}")
        after_report = json.loads((action / "poll/handoff.json").read_text())
        after_position, after_facing, after_depth, after_grid, after_hp = observe(after_report)
        entry = {"key": key, "before": list(position), "facing_before": list(facing),
                 "tile_before": tile, "depth_before": depth, "hp_before": hp,
                 "after": list(after_position), "facing_after": list(after_facing),
                 "tile_after": after_grid[after_position[1] * 11 + after_position[0]],
                 "depth_after": after_depth, "hp_after": after_hp,
                 "key_report": str(action / "key/handoff.json"),
                 "poll_report": str(action / "poll/handoff.json")}
        history.append(entry)
        (OUTPUT / "route.json").write_text(json.dumps(history, indent=2) + "\n")
        print(f"{index + 1:02d} key=${key:02X} {position} {facing} → {after_position} {after_facing} "
              f"tile=${entry['tile_after']:02X} HP={after_hp}", flush=True)
        source = action / "poll/handoff.json"
    else:
        raise RuntimeError(f"stairs not reached in {max_actions} actions")
    (OUTPUT / "stairs-source.json").write_text(json.dumps({"source_report": str(source)}, indent=2) + "\n")
    if facing == (1, 0):
        horizontal = ROOT / "build/traces/dng-stairs-horizontal"
        horizontal.mkdir(parents=True, exist_ok=True)
        with (horizontal / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
            if press_key(75, horizontal / "key", source, probe_stair=True):
                raise RuntimeError(f"horizontal K failed; see {horizontal / 'trace.log'}")
            if next_poll(horizontal / "key/handoff.json", horizontal / "poll"):
                raise RuntimeError(f"horizontal K next poll failed; see {horizontal / 'trace.log'}")
        print("horizontal-facing K refusal captured", flush=True)
    turn = OUTPUT / "stairs-turn"
    turn.mkdir(exist_ok=True)
    turn_key = 0x20 if facing == (0, 1) else direction_key(facing, (0, 1))
    with (turn / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
        if press_key(turn_key, turn / "key", source):
            raise RuntimeError(f"stair turn failed; see {turn / 'trace.log'}")
        if next_poll(turn / "key/handoff.json", turn / "poll"):
            raise RuntimeError(f"stair turn next poll failed; see {turn / 'trace.log'}")
    ready = json.loads((turn / "poll/handoff.json").read_text())
    ready_position, ready_facing, ready_depth, ready_grid, _ = observe(ready)
    if (ready_position != GOAL or ready_facing != (0, 1) or ready_depth != 1 or
            ready_grid[GOAL[1] * 11 + GOAL[0]] != 7):
        raise RuntimeError("stair turn did not leave player facing south on $07")
    descent_report = ROOT / "build/traces/dng-stairs-k/handoff.json"
    if stair_k(turn / "poll/handoff.json", descent_report.parent):
        raise RuntimeError("descent K replay failed")
    ascent_report = ROOT / "build/traces/dng-level2-ascend/handoff.json"
    if stair_k(descent_report, ascent_report.parent, expected_tile="08",
               expected_depth="02", branch="ascend"):
        raise RuntimeError("level-two ascent K replay failed")
    print("dungeon stair round trip complete", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG descent route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
