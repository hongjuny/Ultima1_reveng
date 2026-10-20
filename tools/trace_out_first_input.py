#!/usr/bin/env python3
"""Trace OUT initialization to its first outdoor key poll."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-entry" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-first-input"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or prior["final_cpu"].split()[0] != "pc=8956":
        raise RuntimeError("source trace did not reach OUT entry")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("OUT entry snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"first-input.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8956:
                    raise RuntimeError("snapshot is not at OUT entry")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "OUT initialization complete", (0x898A,)))
                    points.append(wait_at(client, "OUT main loop", (0x89A1,)))
                    points.append(wait_at(client, "outdoor key poll", (0x8A6C, 0x89E8)))
                    if points[-1]["pc"] == "0x89E8":
                        print("OUT took the alternate startup path at $89E8", flush=True)
                    else:
                        print(f"OUT poll stub: {client.mem(0x15C5, 3).hex(' ')}", flush=True)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"OUT first-input trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
                state = {"health_7EC6_7EC7": client.mem(0x7EC6, 2).hex(),
                         "food_7EE5_7EE6": client.mem(0x7EE5, 2).hex(),
                         "poll_stub_15C5": client.mem(0x15C5, 3).hex()}
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "first-input.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout, "state": state,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT first-input trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
