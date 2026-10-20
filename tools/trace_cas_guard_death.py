#!/usr/bin/env python3
"""Force lethal guard damage with a one-byte private player-HP change."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-attack-effect" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-guard-death"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["handler_return_snapshot"]
    if prior["timeout"] is not None or source is None:
        raise RuntimeError("handler return snapshot unavailable")
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
    pending = OUTPUT / f"death.pending-{os.getpid()}.a2state"
    pre_pending = OUTPUT / f"before-hp.pending-{os.getpid()}.a2state"
    post_pending = OUTPUT / f"after-hp.pending-{os.getpid()}.a2state"
    for path in (pending, pre_pending, post_pending):
        path.unlink(missing_ok=True)
    points = []
    timeout = None
    before_hp = None
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
                client.ok("set-turbo 8")
                try:
                    point = wait_at(client, "before player HP subtraction", (0x99CB,))
                    point["hp"] = list(client.mem(0x7EC6, 2))
                    point["damage"] = client.mem(0x73, 1)[0]
                    points.append(point)
                    if point["hp"] != [0x96, 0] or point["damage"] != 0x0F:
                        raise RuntimeError("original guard hit differs")
                    before_hp = point["hp"][0]
                    client.ok(f"save-state {pre_pending}")
                    wait_for_snapshot(pre_pending)
                    client.set_mem(0x7EC6, bytes((0x0A,)))
                    if client.mem(0x7EC6, 2) != bytes((0x0A, 0)):
                        raise RuntimeError("private HP change failed")
                    client.ok(f"save-state {post_pending}")
                    wait_for_snapshot(post_pending)
                    for label, address in (("low HP stored", 0x99D4),
                                           ("borrow decision", 0x99DC),
                                           ("death path", 0x8A41),
                                           ("common module selector", 0x88F8),
                                           ("selector decision", 0x88FD)):
                        point = wait_at(client, label, (address,))
                        point["hp"] = list(client.mem(0x7EC6, 2))
                        points.append(point)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS guard death stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "death.a2state"
    pending.replace(final)
    intervention = None
    if timeout is None:
        pre = OUTPUT / "before-hp.a2state"
        post = OUTPUT / "after-hp.a2state"
        pre_pending.replace(pre)
        post_pending.replace(post)
        intervention = {"before": {"path": str(pre), **describe(pre)},
                        "after": {"path": str(post), **describe(post)}}
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "controlled_change": {"address": "0x7EC6", "before": before_hp,
                                    "after": 0x0A},
              "intervention_snapshots": intervention,
              "checkpoints": points, "timeout": timeout,
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for point in points:
        print(point["label"], point["cpu"], "HP", point["hp"])
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS guard death failed: {error}", file=sys.stderr)
        raise SystemExit(1)
