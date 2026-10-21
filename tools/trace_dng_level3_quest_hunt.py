#!/usr/bin/env python3
"""Hunt the actual level-three slot-5 monster with one accepted quest flag."""

from collections import deque
import contextlib
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_dng_after_up import main as next_poll
from trace_dng_descend import direction_key, observe
from trace_dng_key_w import main as press_key
from trace_startup import cpu_pc
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/dng-level3-entry/handoff.json"
OUTPUT = ROOT / "build/traces/dng-level3-quest-hunt"
DELTAS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def prepare():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
        raise RuntimeError("source is not at level-three input")
    item, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(item["path"]), Path(disk_item["path"])
    for record, path in ((item, snapshot), (disk_item, disk)):
        if describe(path) != {"size": record["size"], "sha256": record["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "prepare.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8DDA:
                    raise RuntimeError("restored level-three input differs")
                if client.mem(0xA506, 1) != b"\x03" or client.mem(0x7EAA, 1) != b"\x00":
                    raise RuntimeError("depth or quest state differs")
                client.set_mem(0x7EAA, b"\x01")
                path = OUTPUT / "accepted.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
            finally:
                client.s.close()
        finally:
            stop(process)
    report = dict(prior)
    report["source_snapshot"] = prior["snapshot"]
    report["snapshot"] = {"path": str(path), **describe(path)}
    report["intervention"] = {"address": "0x7EAA", "before": 0, "after": 1}
    report_path = OUTPUT / "accepted.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report_path


def shortest_to_adjacent(grid, start, target):
    occupied = {i for i, value in enumerate(grid) if value >= 0x10}
    candidates = {(target[0] + dx, target[1] + dy)
                  for dx, dy in DELTAS}
    candidates = {p for p in candidates if 0 <= p[0] < 11 and 0 <= p[1] < 11 and
                  (grid[p[1] * 11 + p[0]] & 0x0F) not in (1, 3) and
                  (p[1] * 11 + p[0]) not in occupied}
    queue = deque([start])
    parents = {start: None}
    while queue:
        point = queue.popleft()
        if point in candidates:
            path = []
            while point != start:
                path.append(point)
                point = parents[point]
            return path[::-1]
        for dx, dy in DELTAS:
            dest = point[0] + dx, point[1] + dy
            if dest in parents or not (0 <= dest[0] < 11 and 0 <= dest[1] < 11):
                continue
            index = dest[1] * 11 + dest[0]
            if (grid[index] & 0x0F) in (1, 3) or index in occupied:
                continue
            parents[dest] = point
            queue.append(dest)
    return None


def play(key, source, action):
    action.mkdir(parents=True, exist_ok=True)
    with (action / "trace.log").open("w") as log, contextlib.redirect_stdout(log):
        if press_key(key, action / "key", source, probe_move=key == 0x0B):
            raise RuntimeError(f"dungeon key failed; see {action / 'trace.log'}")
        key_report = action / "key/handoff.json"
        ram = main_ram(Path(json.loads(key_report.read_text())["snapshot"]["path"]))
        if ram[0x7EAA] == 0xFF:
            return key_report, True
        if next_poll(key_report, action / "poll"):
            raise RuntimeError(f"dungeon next poll failed; see {action / 'trace.log'}")
    return action / "poll/handoff.json", False


def main(max_actions=80):
    source = prepare()
    history = []
    for number in range(1, max_actions + 1):
        report = json.loads(source.read_text())
        position, facing, depth, grid, hp = observe(report)
        ram = main_ram(Path(report["snapshot"]["path"]))
        slot = 5
        target = (ram[0xA50E + slot], ram[0xA514 + slot])
        monster_hp = int.from_bytes(bytes((ram[0xA51A + slot],
                                           ram[0xA520 + slot])), "little")
        if depth != 3 or hp <= 0 or ram[0x7EAA] != 1:
            raise RuntimeError(f"unexpected depth/HP/quest: {depth}/{hp}/{ram[0x7EAA]}")
        path = shortest_to_adjacent(grid, position, target)
        if path is None:
            key = 0x20
        elif path:
            desired = (path[0][0] - position[0], path[0][1] - position[1])
            key = direction_key(facing, desired)
        else:
            desired = (target[0] - position[0], target[1] - position[1])
            key = 65 if desired == facing else direction_key(facing, desired)
        output = OUTPUT / f"action-{number:03d}"
        next_source, completed = play(key, source, output)
        after = json.loads(next_source.read_text())
        after_ram = main_ram(Path(after["snapshot"]["path"]))
        entry = {"number": number, "key": key, "before_position": list(position),
                 "before_facing": list(facing), "before_hp": hp,
                 "target": list(target), "monster_hp": monster_hp,
                 "source_report": str(source), "result_report": str(next_source),
                 "quest_after": after_ram[0x7EAA], "completed": completed}
        history.append(entry)
        (OUTPUT / "route.json").write_text(json.dumps(history, indent=2) + "\n")
        print(f"{number:02d} key=${key:02X} player={position} face={facing} "
              f"slot5={target} hp={monster_hp} quest={after_ram[0x7EAA]:02X}", flush=True)
        if completed:
            print(f"depth-three quest completed after {number} actions", flush=True)
            return 0
        source = next_source
    raise RuntimeError(f"quest target not defeated in {max_actions} actions")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG level-three quest hunt failed: {error}", file=sys.stderr)
        raise SystemExit(1)
