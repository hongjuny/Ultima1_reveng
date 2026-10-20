#!/usr/bin/env python3
"""Replay a castle direction key through collision and turn update."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-first-input" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-step-right"
WATCH = (0x00, 0x01, 0x0C, 0x0D, 0x7EDA, 0x7EDB, 0x7EE4, 0x7EE5,
         0x7EC6, 0x7EC7)


def watched(client) -> dict:
    return {f"${address:04X}": client.mem(address, 1)[0] for address in WATCH}


HANDLERS = {0x0B: (0, 0x8A93), 0x0A: (2, 0x8A9A),
            0x15: (4, 0x8AA1), 0x08: (6, 0x8AA8)}


def main(key: int = 0x15, source_report: Path = SOURCE,
         output: Path = OUTPUT) -> int:
    if key not in HANDLERS:
        raise ValueError(f"not a castle direction key: ${key:02X}")
    index, handler = HANDLERS[key]
    prior = json.loads(source_report.read_text())
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

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"direction.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    collision_cpu = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A27:
                    raise RuntimeError("restored castle poll differs")
                before = watched(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok(f"key {key}")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A2F or f" a={key:02X} " not in cpu:
                        raise RuntimeError(f"direction key did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A2F",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    points.append(wait_at(client, "command lookup return", (0x8A4A,)))
                    if f" x={index:02X} " not in points[-1]["cpu"]:
                        raise RuntimeError("direction key mapped to unexpected offset")
                    points.append(wait_at(client, "patched call", (0x8A56,)))
                    if client.mem(0x8A56, 3) != bytes((0x20, handler & 0xFF, handler >> 8)):
                        raise RuntimeError("direction key dispatch pointer differs")
                    points.append(wait_at(client, "direction handler", (handler,)))
                    points.append(wait_at(client, "proposed movement", (0x8C00,)))
                    points.append(wait_at(client, "collision test return", (0x8C11,)))
                    collision_cpu = points[-1]["cpu"]
                    points.append(wait_at(client, "movement branch", (0x8C29, 0x8C13)))
                    if points[-1]["pc"] == "0x8C29":
                        points.append(wait_at(client, "turn update", (0x8C3F,)))
                    else:
                        points.append(wait_at(client, "blocked turn update", (0x8C3F,)))
                    points.append(wait_at(client, "handler return", (0x8A59,)))
                    points.append(wait_at(client, "main loop", (0x8A31,)))
                    points.append(wait_at(client, "next key poll", (0x8A27,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS direction ${key:02X} trace stopped: {timeout}", flush=True)
                after = watched(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / f"step-{key:02x}.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": key, "at_pc": "0x8A27"},
              "checkpoints": points, "timeout": timeout,
              "collision_cpu": collision_cpu,
              "watched_before": before, "watched_after": after,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"watched: {before} → {after}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS direction trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
