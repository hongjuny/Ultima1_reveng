#!/usr/bin/env python3
"""Trace post-attack guard response to the player HP write."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-attack-effect" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-guard-retaliation"
WATCH = (0x00, 0x01, 0x7EC6, 0x7EC7, 0x7EDA, 0x7EE4, 0x7EE5,
         0x72, 0x73, 0x9E2A, 0x9E29, 0x9E2B)


def watched(client) -> dict:
    return {f"${address:04X}": client.mem(address, 1)[0] for address in WATCH}


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or prior["handler_return_snapshot"] is None:
        raise RuntimeError("handler return snapshot unavailable")
    source = prior["handler_return_snapshot"]
    disk_item = prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"guard.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A59:
                    raise RuntimeError("restored handler return differs")
                before = watched(client)
                client.ok("set-turbo 8")
                try:
                    for label, address in (("post-handler update", 0x9804),
                                           ("guard attack", 0x9933),
                                           ("guard hit", 0x998F),
                                           ("player HP subtraction", 0x99CB),
                                           ("player HP store complete", 0x99D4),
                                           ("next key poll", 0x8A27)):
                        point = wait_at(client, label, (address,))
                        point["watched"] = watched(client)
                        points.append(point)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS guard retaliation stopped: {timeout}", flush=True)
                after = watched(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "guard.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "watched_before": before, "watched_after": after,
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for point in points:
        print(point["label"], point["cpu"],
              "HP", point["watched"]["$7EC6"],
              "damage", point["watched"]["$0073"])
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS guard retaliation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
