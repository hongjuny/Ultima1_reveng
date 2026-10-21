#!/usr/bin/env python3
"""Capture random HP factors for ordinary level-two and level-three spawns."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


CASES = (
    ("level2", ROOT / "build/traces/dng-descend/stairs-turn/poll/handoff.json"),
    ("level3", ROOT / "build/traces/dng-level2-to3/action-011/poll/handoff.json"),
)


def watched(client, label, address):
    slot = client.mem(0xA4FE, 1)[0]
    depth = client.mem(0xA506, 1)[0]
    return {
        "label": label,
        "pc": f"0x{address:04X}",
        "cpu": client.ok("get-cpu"),
        "slot": slot,
        "depth": depth,
        "coefficient": client.mem(0xA60D + depth, 1)[0],
        "random_bound_69": client.mem(0x69, 1)[0],
        "base_hp_a4f2_a4f3": client.mem(0xA4F2, 2).hex(),
        "slot_hp": client.mem(0xA51A + slot, 1)[0] +
                   256 * client.mem(0xA520 + slot, 1)[0] if 1 <= slot <= 5 else None,
        "flags": client.mem(0xA509, 5).hex(),
    }


def trace_case(label, source_report):
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
        raise RuntimeError(f"{label}: source is not at dungeon key poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    output = ROOT / "build/traces" / f"dng-spawn-hp-{label}"
    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"hp.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    timeout = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8DDA:
                    raise RuntimeError(f"{label}: restored PC differs")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DE4")
                client.ok("key 75")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8DE4 or " a=4B " not in cpu:
                        raise RuntimeError(f"{label}: K did not return from poll: {cpu}")
                    wait_at(client, "spawn initialization", (0x9BED,))
                    for index in range(1, 4):
                        for phase, address in (("bounded draw call", 0x9C3C),
                                               ("raw random byte", 0x8259),
                                               ("bounded draw return", 0x9C3F),
                                               ("slot HP stored", 0x9C54)):
                            wait_at(client, f"spawn {index} {phase}", (address,))
                            checkpoints.append(watched(client, f"spawn {index} {phase}", address))
                    wait_at(client, "next dungeon key poll", (0x8DDA,))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"{label} spawn HP trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "spawn-hp.a2state"
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
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for point in checkpoints:
        print(f"{label} {point['label']}: slot={point['slot']} "
              f"coefficient={point['coefficient']} "
              f"A={point['cpu'].split(' a=')[1][:2]} "
              f"HP={point['slot_hp']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


def main():
    for label, source in CASES:
        if trace_case(label, source):
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, IndexError) as error:
        print(f"DNG deep spawn HP trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
