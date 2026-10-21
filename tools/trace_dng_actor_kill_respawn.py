#!/usr/bin/env python3
"""Trace an ordinary lethal dungeon attack through immediate actor respawn."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-attack-repeat-3/poll/handoff.json"
OUTPUT = ROOT / "build/traces/dng-actor-kill-respawn"


def watched(client, label, address):
    return {
        "label": label,
        "pc": f"0x{address:04X}",
        "cpu": client.ok("get-cpu"),
        "victim_slot_a4f2": client.mem(0xA4F2, 1).hex(),
        "damage_a4f3_a4f4": client.mem(0xA4F3, 2).hex(),
        "spawn_slot_a4fe": client.mem(0xA4FE, 1).hex(),
        "slot1_flag": client.mem(0xA509, 1).hex(),
        "slot1_hp_word": (client.mem(0xA51B, 1) +
                          client.mem(0xA521, 1)).hex(),
        "slot1_x_y": (client.mem(0xA50F, 1) + client.mem(0xA515, 1)).hex(),
        "old_cell_4_1": client.mem(0xB099 + 11 + 4, 1).hex(),
        "new_cell_1_7": client.mem(0xB099 + 7 * 11 + 1, 1).hex(),
        "map_hex": client.mem(0xB099, 121).hex(),
    }


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
        raise RuntimeError("source is not at dungeon key poll")
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
    pending = OUTPUT / f"kill.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    timeout = None
    sequence = (
        ("attack damage", 0x9077),
        ("lethal branch", 0x90A9),
        ("victim removal", 0x93A7),
        ("inactive flag stored", 0x93B2),
        ("old cell restored", 0x93C6),
        ("new slot activated", 0x93DD),
        ("new coordinates accepted", 0x9437),
        ("new map cell written", 0x9447),
        ("handler return", 0x8E0E),
    )
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8DDA:
                    raise RuntimeError("restored DNG PC differs")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DE4")
                client.ok("key 65")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8DE4 or " a=41 " not in cpu:
                        raise RuntimeError(f"A did not return from poll: {cpu}")
                    for label, address in sequence:
                        wait_at(client, label, (address,))
                        checkpoints.append(watched(client, label, address))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG lethal attack trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "kill-respawn.a2state"
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
        print(f"{item['label']}: {item['pc']} flag={item['slot1_flag']} "
              f"HP={item['slot1_hp_word']} damage={item['damage_a4f3_a4f4']} "
              f"xy={item['slot1_x_y']} "
              f"cells={item['old_cell_4_1']},{item['new_cell_1_7']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG lethal attack trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
