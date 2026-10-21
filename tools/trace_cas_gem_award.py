#!/usr/bin/env python3
"""Trace one castle gem award from a controlled completed odd quest."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/cas-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/cas-gem-award"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source does not stop at castle input")
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
                    raise RuntimeError("restored castle poll differs")
                initial = {"position": list(client.mem(0, 2)),
                           "index": client.mem(0x9E3B, 1)[0],
                           "quest": list(client.mem(0x7EA9, 8)),
                           "gems": list(client.mem(0x7E75, 4)),
                           "group": client.mem(0x7E6F, 1)[0]}
                if initial["quest"] != [0] * 8 or initial["gems"] != [0] * 4:
                    raise RuntimeError(f"source state differs: {initial}")
                client.set_mem(0, bytes((31, 6)))
                client.set_mem(0x9E3B, b"\x01")
                client.set_mem(0x7EAA, b"\xFF")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok("key 84")  # T, talk with king
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A2F:
                    raise RuntimeError("T did not return from castle poll")
                points = [wait_at(client, "king tile", (0x92AA,)),
                          wait_at(client, "completed quest", (0x92CC,)),
                          wait_at(client, "reward entry", (0x94E7,)),
                          wait_at(client, "odd quest reward", (0x959D,)),
                          wait_at(client, "gem selector", (0x95BC,)),
                          wait_at(client, "red gem write", (0x963A,)),
                          wait_at(client, "gem write complete", (0x963D,))]
                final = {"quest": list(client.mem(0x7EA9, 8)),
                         "gems": list(client.mem(0x7E75, 4)),
                         "index": client.mem(0x9E3B, 1)[0]}
                path = OUTPUT / "award.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "interventions": [{"address": "0x0000", "before": [0, 9],
                                             "after": [31, 6]},
                                            {"address": "0x9E3B", "before": initial["index"],
                                             "after": 1},
                                            {"address": "0x7EAA", "before": 0,
                                             "after": 255}],
                          "initial": initial, "input": 84,
                          "checkpoints": points, "final": final,
                          "snapshot": {"path": str(path), **describe(path)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"red gem: {initial['gems']} → {final['gems']}; quest {final['quest']}")
    print(f"private trace: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"castle gem trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
