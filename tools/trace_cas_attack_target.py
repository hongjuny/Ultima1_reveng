#!/usr/bin/env python3
"""Replay castle A, then Up, stopping at the adjacent actor attack branch."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-occupied-tile" / "step-02" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-attack-target"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source trace is not at castle input")
    source = prior["snapshot"]
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
    pending = OUTPUT / f"attack.pending-{os.getpid()}.a2state"
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
                before = {"position": list(client.mem(0, 2)),
                          "actor_slot_2": [client.mem(a + 2, 1)[0]
                                           for a in (0xB6BC, 0xB6CC, 0xB6AC)],
                          "tile_1_6": client.mem(0xB400 + 6 * 38 + 1, 1)[0]}
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok("key 65")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A2F or " a=41 " not in cpu:
                        raise RuntimeError(f"A key did not return: {cpu}")
                    points.append({"label": "A poll return", "pc": "0x8A2F", "cpu": cpu})
                    points.append(wait_at(client, "command lookup", (0x8A4A,)))
                    if " x=0C " not in points[-1]["cpu"]:
                        raise RuntimeError("A key mapped to unexpected command offset")
                    points.append(wait_at(client, "patched call", (0x8A56,)))
                    if client.mem(0x8A56, 3) != bytes((0x20, 0x56, 0x8C)):
                        raise RuntimeError("A command handler differs")
                    points.append(wait_at(client, "attack handler", (0x8C56,)))
                    points.append(wait_at(client, "direction poll", (0x8A27,)))
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $8C82")
                    client.ok("key 11")
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8C82 or " a=0B " not in cpu:
                        raise RuntimeError(f"Up key did not return: {cpu}")
                    points.append({"label": "direction return", "pc": "0x8C82", "cpu": cpu})
                    points.append(wait_at(client, "attack ray", (0x8CC9,)))
                    points.append(wait_at(client, "target branch", (0x8D08, 0x8CF7)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS attack-target trace stopped: {timeout}", flush=True)
                after = {"position": list(client.mem(0, 2)),
                         "candidate": list(client.mem(0x0C, 2)),
                         "actor_index": client.mem(0x9E36, 1)[0],
                         "actor_type": client.mem(0xB6AC + 2, 1)[0],
                         "turn": [client.mem(a, 1)[0] for a in (0x7EE4, 0x7EDA)]}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "target.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "inputs": [65, 11], "checkpoints": points, "timeout": timeout,
              "before": before, "after": after, "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"attack target: {before} → {after}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS attack-target trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
