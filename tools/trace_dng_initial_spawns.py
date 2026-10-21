#!/usr/bin/env python3
"""Trace the first floor's three initial actor placements."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-to-dng/handoff.json"
OUTPUT = ROOT / "build/traces/dng-initial-spawns"


def state(client, label, address):
    slot = client.mem(0xA4FE, 1)[0]
    x = client.mem(0xA50E + slot, 1)[0] if 1 <= slot <= 5 else None
    y = client.mem(0xA514 + slot, 1)[0] if 1 <= slot <= 5 else None
    cell = client.mem(0xB099 + 11 * y + x, 1)[0] if x is not None and x < 11 and y < 11 else None
    return {
        "label": label,
        "pc": f"0x{address:04X}",
        "cpu": client.ok("get-cpu"),
        "slot": slot,
        "x": x,
        "y": y,
        "cell": cell,
        "remaining": client.mem(0xA4EE, 1)[0],
        "active_flags": client.mem(0xA509, 5).hex(),
        "type_base": client.mem(0xA507, 1).hex(),
        "actor_hp": client.mem(0xA51A, 6).hex(),
        "map_hex": client.mem(0xB099, 121).hex(),
    }


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8956:
        raise RuntimeError("source is not at DNG entry")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"spawn.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    timeout = None
    sequence = [("spawn initialization", 0x9BED),
                ("all slots inactive", 0x9C11)]
    for index in range(1, 4):
        sequence.extend(((f"spawn {index} accepted", 0x9C82),
                         (f"spawn {index} map write", 0x9C8F),
                         (f"spawn {index} map written", 0x9C92)))
    sequence.append(("generator return", 0x8DE6))
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8956:
                    raise RuntimeError("restored DNG PC differs")
                client.ok("set-turbo 8")
                try:
                    for label, address in sequence:
                        wait_at(client, label, (address,))
                        checkpoints.append(state(client, label, address))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG initial spawn trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "initial-spawns.a2state"
    pending.replace(final)
    report = {
        "source_snapshot": source,
        "working_game_disk": disk_item,
        "checkpoints": checkpoints,
        "timeout": timeout,
        "final_cpu": final_cpu,
        "final_state": final_state,
        "snapshot": {"path": str(final), **describe(final)},
    }
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for item in checkpoints:
        print(f"{item['label']}: {item['pc']} slot={item['slot']} "
              f"at=({item['x']},{item['y']}) cell={item['cell']} "
              f"flags={item['active_flags']} remaining={item['remaining']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG initial spawn trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
