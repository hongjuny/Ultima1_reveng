#!/usr/bin/env python3
"""Replay TM's 1000-HP fight through Mondain's flee transition."""

import json
from pathlib import Path
import sys
import time
from collections import deque

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-gem-command/handoff.json"
OUTPUT = ROOT / "build/traces/tm-phase-transition"
PLAYER_HP = 10000
MAX_TURNS = 43
DIRECTIONS = {(1, 0): 21, (-1, 0): 8, (0, 1): 10, (0, -1): 11}


def state(client):
    return {"player_hp": int.from_bytes(client.mem(0x7EC6, 2), "little"),
            "mondain_hp": int.from_bytes(client.mem(0x7EF4, 2), "little"),
            "phase": client.mem(0x7EF2, 1)[0],
            "gem_destroyed": client.mem(0x95AB, 1)[0],
            "player_position": list(client.mem(0, 2)),
            "mondain_position": list(client.mem(0xB628, 2))}


def route_step(client, player, target):
    """Find a free-cell path to any square cardinally adjacent to Mondain."""
    map_bytes = client.mem(0xA2FC, 231)
    offsets = client.mem(0xA3E3, 11)
    def tile(point):
        x, y = point
        return map_bytes[offsets[y] + x] if 0 <= x < 21 and 0 <= y < 11 else 1
    start = tuple(player)
    goal = {p for dx, dy in DIRECTIONS
            if tile(p := (target[0] + dx, target[1] + dy)) == 0 or p == start}
    queue = deque([start])
    previous = {start: None}
    found = None
    while queue:
        current = queue.popleft()
        if current in goal:
            found = current
            break
        for dx, dy in DIRECTIONS:
            candidate = (current[0] + dx, current[1] + dy)
            if candidate not in previous and tile(candidate) == 0:
                previous[candidate] = current
                queue.append(candidate)
    if found is None or found == start:
        return None
    while previous[found] != start:
        found = previous[found]
    return DIRECTIONS[(found[0] - start[0], found[1] - start[1])]


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9815:
        raise RuntimeError("source is not at TM input")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "combat-result.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9815:
                    raise RuntimeError("restored TM input differs")
                original = state(client)
                client.set_mem(0x7EC6, PLAYER_HP.to_bytes(2, "little"))
                client.ok("set-turbo 8")
                turns = []
                pre_regen = None
                end_reason = None
                for number in range(1, MAX_TURNS + 1):
                    before = state(client)
                    delta = (before["mondain_position"][0]-before["player_position"][0],
                             before["mondain_position"][1]-before["player_position"][1])
                    direction = DIRECTIONS.get(delta)
                    if direction is None:
                        move_key = route_step(client, before["player_position"],
                                              before["mondain_position"])
                        if move_key is None:
                            end_reason = f"no free route to target: {delta}"
                            break
                        client.ok_or_data("break-clear-all")
                        client.ok_or_data("break-exec $8EA2")
                        client.ok(f"key {move_key}")
                        client.ok("wait-paused 15000")
                        if cpu_pc(client.ok("get-cpu")) != 0x8EA2:
                            raise RuntimeError(f"turn {number}: move handler did not return")
                        boundary = wait_at(client, f"turn {number} move next input",
                                           (0x9815, 0x88F8, 0x160D))
                        after = state(client)
                        turns.append({"number": number, "action": "approach",
                                      "input": [move_key], "before": before,
                                      "after": after, "result_pc": "0x8EA2",
                                      "boundary_pc": boundary["pc"]})
                        if number == 40:
                            checkpoint = OUTPUT / "before-regeneration.a2state"
                            checkpoint.unlink(missing_ok=True)
                            client.ok(f"save-state {checkpoint}")
                            wait_for_snapshot(checkpoint)
                            time.sleep(0.2)
                            pre_regen = {"path": str(checkpoint), **describe(checkpoint)}
                        print(f"turn {number}: approach {before['player_position']}→"
                              f"{after['player_position']}, target {after['mondain_position']} "
                              f"HP {before['player_hp']}→{after['player_hp']}", flush=True)
                        if boundary["pc"] in ("0x88F8", "0x160D"):
                            end_reason = "player death"
                            break
                        continue
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $8EDC")
                    client.ok("key 65")
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) != 0x8EDC:
                        raise RuntimeError(f"turn {number}: A did not reach attack handler")
                    wait_at(client, f"turn {number} direction", (0x9815,))
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $9177")
                    client.ok_or_data("break-exec $919A")
                    client.ok_or_data("break-exec $91BC")
                    client.ok_or_data("break-exec $91DC")
                    client.ok(f"key {direction}")
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) not in (0x9177, 0x919A, 0x91BC, 0x91DC):
                        raise RuntimeError(f"turn {number}: direction did not decode")
                    result = wait_at(client, f"turn {number} result", (0x8EA2, 0x9034, 0x9033))
                    if result["pc"] == "0x8EA2":
                        boundary = wait_at(client, f"turn {number} next input",
                                           (0x9815, 0x88F8, 0x160D))
                    else:
                        boundary = result
                    after = state(client)
                    turn = {"number": number, "action": "attack", "input": [65, direction],
                            "before": before, "after": after,
                            "result_pc": result["pc"], "boundary_pc": boundary["pc"]}
                    turns.append(turn)
                    print(f"turn {number}: target {before['mondain_hp']}→{after['mondain_hp']} "
                          f"player {before['player_hp']}→{after['player_hp']} "
                          f"{boundary['pc']}", flush=True)
                    if boundary["pc"] == "0x9034":
                        end_reason = "victory"
                        break
                    if boundary["pc"] == "0x9033":
                        end_reason = "gem gate rejected"
                        break
                    if boundary["pc"] in ("0x88F8", "0x160D"):
                        end_reason = "player death"
                        break
                else:
                    end_reason = "phase-two observation complete"
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "intervention": {"address": "0x7EC6", "player_hp": PLAYER_HP},
                          "original": original, "turns": turns,
                          "pre_regen_snapshot": pre_regen,
                          "end_reason": end_reason, "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM battle result: {end_reason}, {len(turns)} attacks", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM full combat failed: {error}", file=sys.stderr)
        raise SystemExit(1)
