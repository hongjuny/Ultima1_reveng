#!/usr/bin/env python3
"""Use E on the reached code-$07 tile and follow the town selector."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-route-to-07" / "step-29" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-enter-07"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source trace is not at outdoor input")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"enter.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("restored PC differs")
                coords_before = client.mem(0, 2).hex()
                if coords_before != "2b0f":
                    raise RuntimeError(f"not on intended dungeon tile: {coords_before}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A74")
                client.ok("key 69")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A74 or " a=45 " not in cpu:
                        raise RuntimeError(f"E did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A74",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    points.append(wait_at(client, "command path", (0x89CB,)))
                    points.append(wait_at(client, "lookup return", (0x89CE,)))
                    if " x=14 " not in points[-1]["cpu"]:
                        raise RuntimeError("E was not command index 10")
                    points.append(wait_at(client, "E selection", (0x89D0,)))
                    points.append(wait_at(client, "patched call", (0x89DC,)))
                    if client.mem(0x89DC, 3) != bytes((0x20, 0xC8, 0x90)):
                        raise RuntimeError("E did not dispatch to $90C8")
                    points.append(wait_at(client, "E handler", (0x90C8,)))
                    points.append(wait_at(client, "tile code ready", (0x90D5,)))
                    if " a=07 " not in points[-1]["cpu"] or client.mem(0x9DC5, 1) != b"\x07":
                        raise RuntimeError("E did not read tile code $07")
                    points.append(wait_at(client, "location selector", (0x90FF,)))
                    points.append(wait_at(client, "dungeon offset selected", (0x9137,)))
                    if " a=08 " not in points[-1]["cpu"]:
                        raise RuntimeError("tile $07 did not select overlay offset $08")
                    nearby = client.mem(0x7EB1, 4).hex()
                    points.append(wait_at(client, "OUT transition helper", (0x8EFA,)))
                    points.append(wait_at(client, "common module selector", (0x88FD,)))
                except RuntimeError as error:
                    timeout = str(error)
                    nearby = None
                    print(f"OUT E dungeon trace stopped: {timeout}", flush=True)
                coords_after = client.mem(0, 2).hex()
                saved_coords = client.mem(0x7E73, 2).hex()
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "enter-07.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": 69, "at_pc": "0x8A6C"},
              "checkpoints": points, "timeout": timeout,
              "coords_before": coords_before, "coords_after": coords_after,
              "saved_coords_7E73": saved_coords, "nearby_tiles_7EB1": nearby,
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
        print(f"OUT enter-06 trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
