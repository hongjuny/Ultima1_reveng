#!/usr/bin/env python3
"""Test king quest acceptance from a controlled castle-local position."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/cas-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/cas-quest-accept"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source does not stop at the castle poll")
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A27:
                    raise RuntimeError("restored castle input differs")
                before = {"position": list(client.mem(0, 2)),
                          "quest": list(client.mem(0x7EA9, 8)),
                          "world_location": client.mem(0x7EED, 1)[0],
                          "group": client.mem(0x7E6F, 1)[0],
                          "castle_index": client.mem(0x9E3B, 1)[0]}
                if before["position"] != [0, 9] or before["quest"] != [0] * 8:
                    raise RuntimeError(f"castle input state differs: {before}")
                client.set_mem(0, bytes((31, 6)))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok("key 84")  # T, talk
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A2F:
                    raise RuntimeError("T did not return from the key poll")
                points = [wait_at(client, "talk handler", (0x927C,)),
                          wait_at(client, "king tile accepted", (0x92AA,)),
                          wait_at(client, "quest status", (0x92CC,)),
                          wait_at(client, "king prompt input", (0x8A25,))]
                if client.mem(0x7EA9 + before["castle_index"], 1) != b"\x00":
                    raise RuntimeError("quest unexpectedly changed before acceptance")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $9301")
                client.ok("key 83")  # S, service
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x9301:
                    raise RuntimeError("S did not return from the king prompt")
                points.append(wait_at(client, "service choice", (0x93FB,)))
                points.append(wait_at(client, "quest accepted", (0x9437,)))
                points.append(wait_at(client, "quest increment complete", (0x943A,)))
                after = list(client.mem(0x7EA9, 8))
                path = OUTPUT / "accepted.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "intervention": {"address": "0x0000", "before": [0, 9],
                                           "after": [31, 6]},
                          "before": before, "after_quest": after,
                          "inputs": [84, 83], "checkpoints": points,
                          "snapshot": {"path": str(path), **describe(path)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"castle index {before['castle_index']}: quest {before['quest']} → {after}")
    print(f"private trace: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"castle quest trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
