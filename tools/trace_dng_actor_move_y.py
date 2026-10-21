#!/usr/bin/env python3
"""Trace the ordinary slot-3 vertical dungeon move and map writes."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-east-to-03-step-2/handoff.json"
OUTPUT = ROOT / "build/traces/dng-actor-move-y"
MAP = 0xB099


def watched(client, label, address):
    return {
        "label": label,
        "pc": f"0x{address:04X}",
        "cpu": client.ok("get-cpu"),
        "slot": client.mem(0xA4FE, 1).hex(),
        "actor_x": client.mem(0xA511, 1).hex(),
        "actor_y": client.mem(0xA517, 1).hex(),
        "candidate_x": client.mem(0xA4EA, 1).hex(),
        "candidate_y": client.mem(0xA4EB, 1).hex(),
        "saved_destination": client.mem(0xA4F2, 1).hex(),
        "old_cell_3_3": client.mem(MAP + 3 * 11 + 3, 1).hex(),
        "new_cell_3_2": client.mem(MAP + 2 * 11 + 3, 1).hex(),
    }


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8E0E:
        raise RuntimeError("source is not at the dungeon movement handler return")
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
    pending = OUTPUT / f"actor.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    timeout = None
    sequence = (
        ("turn entry", 0x98EC),
        ("old cell read returned", 0x99D6),
        ("old cell low nibble ready", 0x99D9),
        ("old cell restored", 0x99DC),
        ("new y committed", 0x99E5),
        ("destination read and saved", 0x99F4),
        ("destination overlay ready", 0x99FE),
        ("destination overlay stored", 0x9A01),
        ("next dungeon key poll", 0x8DDA),
    )
    with (OUTPUT / "a2m.log").open("w") as log:
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
                    for label, address in sequence:
                        wait_at(client, label, (address,))
                        checkpoints.append(watched(client, label, address))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG vertical movement stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "actor-move-y.a2state"
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
              f"actor=({item['actor_x']},{item['actor_y']}) "
              f"cells={item['old_cell_3_3']},{item['new_cell_3_2']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG vertical movement failed: {error}", file=sys.stderr)
        raise SystemExit(1)
