#!/usr/bin/env python3
"""Continue the verified OUT load through common setup to module entry."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-head-position" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-entry"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or prior["final_cpu"].split()[0] != "pc=892B":
        raise RuntimeError("OUT load did not finish at $892B")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("OUT load snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    expected = (ROOT / "extracted" / "OUT").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"entry.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x892B:
                    raise RuntimeError("snapshot is not at OUT loader caller return")
                if client.mem(0x8956, len(expected)) != expected:
                    raise RuntimeError("OUT bytes differ before common setup")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "post-load helper return", (0x892E,)))
                    points.append(wait_at(client, "OUT entry jump", (0x893C,)))
                    points.append(wait_at(client, "OUT entry", (0x8956,)))
                    print(f"OUT: {len(expected)} bytes loaded at $8956", flush=True)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"OUT entry trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "entry.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "out_bytes": len(expected), "final_cpu": final_cpu,
              "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT entry trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
