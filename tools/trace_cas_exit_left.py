#!/usr/bin/env python3
"""Press left at the castle's initial x=0 and trace the OUT return path."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-first-input" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-exit-left"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source trace is not at castle input")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"exit-left.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A27:
                    raise RuntimeError("restored castle poll differs")
                coords_before = client.mem(0x00, 2).hex()
                edge = client.mem(0xB6BD, 1)[0]
                if coords_before != "0009" or edge < 5:
                    raise RuntimeError("source is not the expected castle entrance")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok("key 8")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A2F or " a=08 " not in cpu:
                        raise RuntimeError(f"left key did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A2F",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    points.append(wait_at(client, "command lookup return", (0x8A4A,)))
                    if " x=06 " not in points[-1]["cpu"]:
                        raise RuntimeError("left key did not map to table offset 6")
                    points.append(wait_at(client, "patched call", (0x8A56,)))
                    if client.mem(0x8A56, 3) != bytes((0x20, 0xA8, 0x8A)):
                        raise RuntimeError("left key did not dispatch to $8AA8")
                    points.append(wait_at(client, "left handler", (0x8AA8,)))
                    points.append(wait_at(client, "x=0 edge branch", (0x8AB3,)))
                    points.append(wait_at(client, "return to OUT", (0x8BFD,)))
                    points.append(wait_at(client, "outdoor selector", (0x88FB,)))
                    points.append(wait_at(client, "module selector", (0x88FD,)))
                    if " a=04 " not in points[-1]["cpu"]:
                        raise RuntimeError("castle exit did not select OUT")
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS exit-left trace stopped: {timeout}", flush=True)
                coords_after = client.mem(0x00, 2).hex()
                saved_outdoor_coords = client.mem(0x7E73, 2).hex()
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "exit-left.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": 8, "at_pc": "0x8A27"},
              "checkpoints": points, "timeout": timeout,
              "coords_before": coords_before, "coords_after": coords_after,
              "edge_tile_B6BD": edge, "saved_outdoor_coords": saved_outdoor_coords,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS exit-left trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
