#!/usr/bin/env python3
"""Inject P at the first outdoor poll and inspect command dispatch."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-first-input" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-key-p"
KEY = 80  # P; semantic meaning is not assumed until dispatch is observed.


def run(key: int = KEY, output: Path = OUTPUT) -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or prior["final_cpu"].split()[0] != "pc=8A6C":
        raise RuntimeError("source trace did not reach OUT key poll")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("OUT first-input snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"key.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("snapshot is not at outdoor poll")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A74")
                client.ok(f"key {key}")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A74:
                        raise RuntimeError(f"key did not return to poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A74",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    print(f"outdoor poll return: $8A74 {cpu}", flush=True)
                    points.append(wait_at(client, "command path", (0x89CB, 0x89A1)))
                    if points[-1]["pc"] == "0x89CB":
                        points.append(wait_at(client, "command lookup return", (0x89CE,)))
                        points.append(wait_at(client, "command decision", (0x89D0, 0x89DF)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"OUT key ${key:02X} trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
                state = {"health_7EC6_7EC7": client.mem(0x7EC6, 2).hex(),
                         "food_7EE5_7EE6": client.mem(0x7EE5, 2).hex(),
                         "key_buffer_0074_0078": client.mem(0x74, 5).hex()}
            finally:
                client.s.close()
        finally:
            stop(process)

    final = output / ("key-p.a2state" if key == KEY else f"key-{key:02x}.a2state")
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": key, "at_pc": "0x8A6C"},
              "checkpoints": points, "timeout": timeout, "state": state,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT key-P trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
