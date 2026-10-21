#!/usr/bin/env python3
"""Route around the TM wall and re-engage Mondain after recovery."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from trace_tm_phase_transition import DIRECTIONS, route_step, state


SOURCE = ROOT / "build/traces/tm-phase1-return/handoff.json"
OUTPUT = ROOT / "build/traces/tm-reengage"
MAX_ACTIONS = 30


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
    final = OUTPUT / "result.a2state"
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
                client.ok("set-turbo 8")
                turns = []
                end_reason = "action limit"
                for number in range(1, MAX_ACTIONS + 1):
                    before = state(client)
                    delta = (before["mondain_position"][0]-before["player_position"][0],
                             before["mondain_position"][1]-before["player_position"][1])
                    direction = DIRECTIONS.get(delta)
                    if direction is None:
                        key = route_step(client, before["player_position"],
                                         before["mondain_position"])
                        if key is None:
                            end_reason = "no route to adjacent cell"
                            break
                        client.ok_or_data("break-clear-all")
                        client.ok_or_data("break-exec $8EA2")
                        client.ok(f"key {key}")
                        client.ok("wait-paused 15000")
                        if cpu_pc(client.ok("get-cpu")) != 0x8EA2:
                            raise RuntimeError(f"action {number}: move handler did not return")
                        input_keys = [key]
                        action = "approach"
                        result = "0x8EA2"
                    else:
                        client.ok_or_data("break-clear-all")
                        client.ok_or_data("break-exec $8EDC")
                        client.ok("key 65")
                        client.ok("wait-paused 15000")
                        if cpu_pc(client.ok("get-cpu")) != 0x8EDC:
                            raise RuntimeError(f"action {number}: attack handler absent")
                        wait_at(client, f"action {number} direction", (0x9815,))
                        client.ok_or_data("break-clear-all")
                        client.ok_or_data("break-exec $8EA2")
                        client.ok_or_data("break-exec $9034")
                        client.ok(f"key {direction}")
                        client.ok("wait-paused 15000")
                        result = f"0x{cpu_pc(client.ok('get-cpu')):04X}"
                        input_keys = [65, direction]
                        action = "attack"
                    if result == "0x9034":
                        boundary = result
                    else:
                        boundary = wait_at(client, f"action {number} next input",
                                           (0x9815, 0x88F8, 0x160D))["pc"]
                    after = state(client)
                    turns.append({"number": number, "action": action,
                                  "input": input_keys, "before": before, "after": after,
                                  "result_pc": result, "boundary_pc": boundary})
                    print(f"action {number} {action}: player {before['player_position']}→"
                          f"{after['player_position']} HP {before['player_hp']}→"
                          f"{after['player_hp']}; Mondain {before['mondain_position']}→"
                          f"{after['mondain_position']} HP {before['mondain_hp']}→"
                          f"{after['mondain_hp']} phase {after['phase']}", flush=True)
                    if after["phase"] != 1:
                        end_reason = "phase changed"
                        break
                    if boundary != "0x9815":
                        end_reason = f"stopped at {boundary}"
                        break
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "turns": turns, "end_reason": end_reason,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM re-engage: {end_reason} after {len(turns)} actions", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM re-engage failed: {error}", file=sys.stderr)
        raise SystemExit(1)
