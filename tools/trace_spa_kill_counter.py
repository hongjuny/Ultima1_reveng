#!/usr/bin/env python3
"""Replay SPA Fire with an existing ship at the count-1 and count-20 gates."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_spa_command_survey import OUTPUT as SURVEY_OUTPUT, checked
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build/traces/spa-kill-counter"
TRIALS = {"first_hit": 0, "ace_twentieth": 19}
SHIP_CELL = 0xB099 + 25  # Existing nonzero ship at sector (3,2).


def sample(client):
    return {f"${addr:04X}": client.mem(addr, 1)[0]
            for addr in (0x0000, 0x0001, 0x7EB6, 0x7EE7, 0x7EE8,
                         0x7EE9, 0x7EEA, 0x9286, 0x93F1, 0x93F2,
                         0x93F3, 0x00BA, 0x00BB, SHIP_CELL)}


def trial(name, starting_count, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("source is not SPA first input")
                source_state = sample(client)
                if source_state["$7EB6"] != 0 or source_state[f"${SHIP_CELL:04X}"] != 0xC0:
                    raise RuntimeError(f"source ship or counter changed: {source_state}")
                # Move to an existing ship's sector. No ship data is altered.
                client.set_mem(0x0000, bytes((3, 2)))
                client.set_mem(0x7EB6, bytes((starting_count,)))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok("key 86")  # V opens the view/input mode.
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A62:
                    raise RuntimeError("V key was not accepted")
                points = [wait_at(client, "SPA view poll", (0x9361,))]
                view_state = sample(client)
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $93B5")
                client.ok("key 70")  # F fires from this view.
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x93B5:
                    raise RuntimeError("F key was not decoded")
                points.append(wait_at(client, "Fire handler", (0x964D,)))
                points.append(wait_at(client, "target count read", (0x9675,)))
                before = sample(client)
                # The view had decoded the old sector before the move. Supply
                # the already-present ship's high two-bit count from $B0B2.
                ship_count = before[f"${SHIP_CELL:04X}"] >> 6
                if ship_count != 3 or before["$9286"] != 0:
                    raise RuntimeError(f"unexpected visible target state: {before}")
                client.set_mem(0x9286, bytes((ship_count,)))
                points.append(wait_at(client, "target-present branch", (0x967D,)))
                target = sample(client)
                # Aim at the moving target's current screen coordinate. The
                # original geometry, hit, reward, and count logic run below.
                aim = bytes((target["$93F2"], target["$93F3"]))
                client.set_mem(0x00BA, aim)
                points.append(wait_at(client, "hit reward entry", (0x9700,)))
                hit = sample(client)
                cpu = client.ok("get-cpu")
                if " y=19 " not in cpu:
                    raise RuntimeError(f"hit indexed another map cell: {cpu}")
                points.append(wait_at(client, "counter increment", (0x9732,)))
                reward = sample(client)
                points.append(wait_at(client, "ace comparison", (0x973A,)))
                counted = sample(client)
                points.append(wait_at(client, "ace branch", (0x9766, 0x9763)))
                result = sample(client)
                return {"source": source_state, "view": view_state,
                        "before_target": before, "target": target,
                        "aim": list(aim), "hit": hit, "reward": reward,
                        "counted": counted, "result": result,
                        "checkpoints": points, "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    stages = json.loads((SURVEY_OUTPUT / "stages.json").read_text())
    source, disk_item = stages["source_snapshot"], stages["working_game_disk"]
    snapshot, disk = checked(source), checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs = {}
    for name, starting_count in TRIALS.items():
        runs[name] = trial(name, starting_count, emulator, disk, snapshot, Ctl)
        run = runs[name]
        print(f"{name}: count {starting_count}→{run['counted']['$7EB6']}; "
              f"experience {run['before_target']['$7EE7']}→"
              f"{run['counted']['$7EE7']}; "
              f"ship {run['hit'][f'${SHIP_CELL:04X}']:02X}→"
              f"{run['counted'][f'${SHIP_CELL:04X}']:02X}; "
              f"branch {run['checkpoints'][-1]['pc']}", flush=True)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "runs": runs}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"SPA kill counter trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
