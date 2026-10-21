#!/usr/bin/env python3
"""Force a dungeon attack miss by changing one private RNG state byte."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_cas_guard_miss import next_random
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-east-to-03-step-1/handoff.json"
OUTPUT = ROOT / "build/traces/dng-monster-miss"


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
    pending = OUTPUT / f"miss.pending-{os.getpid()}.a2state"
    before_pending = OUTPUT / f"before-rng.pending-{os.getpid()}.a2state"
    after_pending = OUTPUT / f"after-rng.pending-{os.getpid()}.a2state"
    for path in (pending, before_pending, after_pending):
        path.unlink(missing_ok=True)
    points = []
    timeout = None
    state = bytes(16)
    chosen = original = predicted = threshold = None
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
                before_hp = client.mem(0x7EC6, 2).hex()
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "monster hit RNG call", (0x9A5C,)))
                    threshold = client.mem(0xA4F2, 1)[0]
                    state = client.mem(0x1E18, 16)
                    client.ok(f"save-state {before_pending}")
                    wait_for_snapshot(before_pending)
                    original = next_random(state)
                    if original != 0xA6 or threshold != 0x45:
                        raise RuntimeError("original monster hit roll differs")
                    chosen = next((seed for seed in range(256)
                                   if seed != state[15] and
                                   next_random(state[:15] + bytes((seed,))) < threshold), None)
                    if chosen is None:
                        raise RuntimeError("no one-byte seed selects a miss")
                    predicted = next_random(state[:15] + bytes((chosen,)))
                    client.set_mem(0x1E27, bytes((chosen,)))
                    if client.mem(0x1E27, 1)[0] != chosen:
                        raise RuntimeError("private RNG change failed")
                    client.ok(f"save-state {after_pending}")
                    wait_for_snapshot(after_pending)
                    points.append(wait_at(client, "monster miss branch", (0x9A64, 0x9A72)))
                    if points[-1]["pc"] != "0x9A64":
                        raise RuntimeError("controlled seed did not select miss")
                    points.append(wait_at(client, "next dungeon key poll", (0x8DDA,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG monster miss stopped: {timeout}", flush=True)
                after_hp = client.mem(0x7EC6, 2).hex()
                position = client.mem(0xA4E8, 2).hex()
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "miss.a2state"
    pending.replace(final)
    private_states = None
    if timeout is None:
        before_path, after_path = OUTPUT / "before-rng.a2state", OUTPUT / "after-rng.a2state"
        before_pending.replace(before_path)
        after_pending.replace(after_path)
        private_states = {"before": {"path": str(before_path), **describe(before_path)},
                          "after": {"path": str(after_path), **describe(after_path)}}
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "controlled_change": {"address": "0x1E27", "before": state[15],
                                    "after": chosen, "original_roll": original,
                                    "predicted_roll": predicted, "threshold": threshold},
              "intervention_snapshots": private_states,
              "checkpoints": points, "timeout": timeout,
              "before_hp": before_hp, "after_hp": after_hp, "position": position,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"miss: seed ${state[15]:02X}→${chosen:02X}, "
          f"roll ${original:02X}→${predicted:02X}, threshold ${threshold:02X}")
    print(f"HP: {before_hp} → {after_hp}; position={position}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG monster miss failed: {error}", file=sys.stderr)
        raise SystemExit(1)
