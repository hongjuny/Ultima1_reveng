#!/usr/bin/env python3
"""Follow the completed Space command back to the outdoor input loop."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-space-effect" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-after-space"
WATCH = (0x7EDA, 0x7EDB, 0x7EE4, 0x7EE5, 0x7EE6, 0x7EC6, 0x7EC7)


def watched(client) -> dict:
    return {f"${address:04X}": client.mem(address, 1)[0] for address in WATCH}


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or prior["final_cpu"].split()[0] != "pc=89DF":
        raise RuntimeError("source trace did not return from Space handler")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("Space-effect snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"after-space.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x89DF:
                    raise RuntimeError("snapshot is not at Space handler return")
                before = watched(client)
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "next outdoor frame", (0x8995,)))
                    points.append(wait_at(client, "next main loop", (0x89A1,)))
                    points.append(wait_at(client, "next key poll", (0x8A6C, 0x89E8)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"OUT after-Space trace stopped: {timeout}", flush=True)
                after = watched(client)
                print(f"watched state: {before} → {after}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "after-space.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "watched_before": before, "watched_after": after,
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
        print(f"OUT after-Space trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
