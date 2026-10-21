#!/usr/bin/env python3
"""Replay one outdoor landmark completing an accepted castle quest."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/out-landmark-quest"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source does not stop at OUT input")
    snapshot, disk = checked(prior["snapshot"]), checked(prior["working_game_disk"])
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("restored outdoor poll differs")
                initial = {"position": list(client.mem(0, 2)),
                           "quest": list(client.mem(0x7EA9, 8)),
                           "target_tile": client.mem(0x6000 + 3 * 64 + 59, 1)[0]}
                if initial["quest"] != [0] * 8 or initial["target_tile"] != 0x0A:
                    raise RuntimeError(f"source quest or landmark differs: {initial}")
                client.set_mem(0, bytes((59, 3)))
                client.set_mem(0x7EA9, b"\x01")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A74")
                client.ok("key 69")  # E, enter landmark
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A74:
                    raise RuntimeError("E did not return from outdoor poll")
                points = [wait_at(client, "enter gate", (0x90C8,)),
                          wait_at(client, "landmark match", (0x913A,)),
                          wait_at(client, "quest write", (0x915F,)),
                          wait_at(client, "quest write complete", (0x9162,))]
                state = {"world_location": client.mem(0x7EED, 1)[0],
                         "quest": list(client.mem(0x7EA9, 8)),
                         "position": list(client.mem(0, 2))}
                path = OUTPUT / "completed.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "interventions": [{"address": "0x0000", "before": initial["position"],
                                             "after": [59, 3]},
                                            {"address": "0x7EA9", "before": 0, "after": 1}],
                          "initial": initial, "input": 69, "checkpoints": points,
                          "state": state,
                          "snapshot": {"path": str(path), **describe(path)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"landmark quest: {state}")
    print(f"private trace: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"landmark quest trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
