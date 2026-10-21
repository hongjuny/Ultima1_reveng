#!/usr/bin/env python3
"""Trace the first observed dungeon HP loss after moving to (3,1)."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-east-to-03-step-1/handoff.json"
OUTPUT = ROOT / "build/traces/dng-monster-turn"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8E0E:
        raise RuntimeError("source is not at dungeon movement handler return")
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
    pending = OUTPUT / f"monster.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    hp = []
    timeout = None
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
                    for label, address in (("turn routine", 0x98EC),
                                           ("monster attack", 0x9A0A),
                                           ("HP low-byte store", 0x9B0C),
                                           ("HP stores complete", 0x9B1A),
                                           ("next dungeon loop", 0x8DE6),
                                           ("next dungeon key poll", 0x8DDA)):
                        points.append(wait_at(client, label, (address,)))
                        hp.append({"pc": f"0x{address:04X}",
                                   "hp_7EC6_7EC7": client.mem(0x7EC6, 2).hex(),
                                   "damage_a4f2_a4f3": client.mem(0xA4F2, 2).hex(),
                                   "actor_index_a4fe": client.mem(0xA4FE, 1).hex()})
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG monster trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "monster-turn.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "watched": hp, "timeout": timeout,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for item in hp:
        print(item)
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG monster trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
