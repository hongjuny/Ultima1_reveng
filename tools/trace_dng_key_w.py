#!/usr/bin/env python3
"""Replay a key at a DNG poll and inspect the command dispatch."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/dng-key-w"


def main(key: int = 87, output: Path = OUTPUT,
         source_report: Path = SOURCE, probe_move: bool = False,
         probe_stair: bool = False) -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
        raise RuntimeError("source is not at first DNG key poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"key-{key:02x}.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    patched = None
    before = None
    after = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8DDA:
                    raise RuntimeError("restored DNG PC differs")
                before = {"position": client.mem(0xA4E8, 2).hex(),
                          "facing": client.mem(0xA4EC, 2).hex(),
                          "hp": client.mem(0x7EC6, 2).hex(),
                          "food": client.mem(0x7EE5, 2).hex()}
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DE4")
                client.ok(f"key {key}")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8DE4 or f" a={key:02X} " not in cpu:
                        raise RuntimeError(f"key did not return from poll: {cpu}")
                    points.append({"label": "key poll return", "pc": "0x8DE4",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    points.append(wait_at(client, "lookup call", (0x8DD4,)))
                    points.append(wait_at(client, "lookup return", (0x8DD7,)))
                    points.append(wait_at(client, "command decision", (0x8E0B, 0x8D99)))
                    if points[-1]["pc"] == "0x8E0B":
                        patched = client.mem(0x8E0B, 3).hex()
                        target = int.from_bytes(client.mem(0x8E0C, 2), "little")
                        points.append(wait_at(client, "command handler", (target,)))
                        if probe_move and target == 0x8E95:
                            points.append(wait_at(client, "candidate tile", (0x8E9B,)))
                            points.append(wait_at(client, "movement branch", (0x8EA7, 0x8EBE)))
                        if probe_stair and target == 0x961B:
                            points.append(wait_at(client, "stair facing check", (0x963F,)))
                            points.append(wait_at(client, "stair gate or return", (0x9666, 0x8E0E)))
                            if points[-1]["pc"] == "0x9666":
                                raise RuntimeError("stair passed facing check; use transition tracer")
                        else:
                            points.append(wait_at(client, "handler return", (0x8E0E,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG key trace stopped: {timeout}", flush=True)
                after = {"position": client.mem(0xA4E8, 2).hex(),
                         "facing": client.mem(0xA4EC, 2).hex(),
                         "hp": client.mem(0x7EC6, 2).hex(),
                         "food": client.mem(0x7EE5, 2).hex()}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / f"key-{key:02x}.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": key, "at_pc": "0x8DDA"},
              "checkpoints": points, "timeout": timeout, "patched_call": patched,
              "state_before": before, "state_after": after,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG W trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
