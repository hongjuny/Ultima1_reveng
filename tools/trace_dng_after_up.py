#!/usr/bin/env python3
"""Continue a completed DNG command to the next key poll."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-key-up/handoff.json"
OUTPUT = ROOT / "build/traces/dng-after-up"


def main(source_report: Path = SOURCE, output: Path = OUTPUT) -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8E0E:
        raise RuntimeError("source is not at DNG Up handler return")
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
    pending = output / f"after-input.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x8E0E:
                    raise RuntimeError("restored DNG PC differs")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "next dungeon loop", (0x8DE6,)))
                    points.append(wait_at(client, "next dungeon key read", (0x8DDA,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG after-Up trace stopped: {timeout}", flush=True)
                state = {"position": client.mem(0xA4E8, 2).hex(),
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
    final = output / "after-input.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout, "state": state,
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
        print(f"DNG after-Up trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
