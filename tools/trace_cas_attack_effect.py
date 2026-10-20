#!/usr/bin/env python3
"""Continue the castle attack through hit/miss and the next input poll."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-attack-target" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-attack-effect"
WATCH = (0x00, 0x01, 0x7EDA, 0x7EE4, 0x7EE5, 0x7EC6,
         0xB6AE, 0xB6BE, 0xB6CE, 0xB6DE, 0xB6EE, 0x9E2A, 0x9E36)


def watched(client) -> dict:
    return {f"${address:04X}": client.mem(address, 1)[0] for address in WATCH}


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8D08:
        raise RuntimeError("source trace is not at attack target branch")
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
    return_pending = OUTPUT / f"handler-return.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    return_pending.unlink(missing_ok=True)
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
                if cpu_pc(client.ok("get-cpu")) != 0x8D08:
                    raise RuntimeError("restored attack branch differs")
                before = watched(client)
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "hit or miss", (0x8D27, 0x8CF7)))
                    if points[-1]["pc"] == "0x8D27":
                        points.append(wait_at(client, "damage or kill", (0x8D71, 0x8D84, 0x8D9A)))
                    points.append(wait_at(client, "attack handler return", (0x8A59,)))
                    at_handler_return = watched(client)
                    client.ok(f"save-state {return_pending}")
                    wait_for_snapshot(return_pending)
                    points.append(wait_at(client, "next key poll", (0x8A27,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS attack effect stopped: {timeout}", flush=True)
                after = watched(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "effect.a2state"
    pending.replace(final)
    return_snapshot = None
    if timeout is None:
        return_final = OUTPUT / "handler-return.a2state"
        return_pending.replace(return_final)
        return_snapshot = {"path": str(return_final), **describe(return_final)}
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "watched_before": before, "watched_at_handler_return":
              at_handler_return if timeout is None else None,
              "handler_return_snapshot": return_snapshot,
              "watched_after": after,
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"watched: {before} → {after}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS attack effect failed: {error}", file=sys.stderr)
        raise SystemExit(1)
