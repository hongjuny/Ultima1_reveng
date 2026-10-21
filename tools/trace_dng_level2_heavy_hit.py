#!/usr/bin/env python3
"""Trace all ordinary monster-attack events after a dungeon command."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-level2-to3/action-004/key/handoff.json"
OUTPUT = ROOT / "build/traces/dng-level2-heavy-hit"
WATCH = (0x9A0A, 0x9A62, 0x9A64, 0x9A72, 0x9A95, 0x9B0C, 0x9B1A, 0x8DDA)


def main(source_report: Path = SOURCE, output: Path = OUTPUT) -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8E0E:
        raise RuntimeError("source is not at second-floor handler return")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"heavy-hit.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    events = []
    timeout = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8E0E:
                    raise RuntimeError("restored second-floor PC differs")
                before_hp = client.mem(0x7EC6, 2).hex()
                client.ok("set-turbo 8")
                try:
                    for index in range(50):
                        candidates = WATCH + ((0x9AAC,) if events and
                                              events[-1]["pc"] == "0x9A95" else ())
                        point = wait_at(client, f"combat event {index + 1}", candidates)
                        point.update({"hp": client.mem(0x7EC6, 2).hex(),
                                      "damage": client.mem(0xA4F2, 2).hex(),
                                      "roll": client.mem(0xA4F0, 2).hex(),
                                      "threshold": client.mem(0xA4FC, 1).hex(),
                                      "actor_index": client.mem(0xA4FE, 1).hex(),
                                      "depth": client.mem(0xA506, 1).hex()})
                        events.append(point)
                        if point["pc"] == "0x8DDA":
                            break
                    else:
                        raise RuntimeError("combat trace exceeded 50 events")
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"second-floor combat trace stopped: {timeout}", flush=True)
                after_hp = client.mem(0x7EC6, 2).hex()
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "heavy-hit.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "events": events, "before_hp": before_hp, "after_hp": after_hp,
              "timeout": timeout, "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"HP {before_hp} → {after_hp}; private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG level-two heavy-hit trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
