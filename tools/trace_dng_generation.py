#!/usr/bin/env python3
"""Observe DNG template copy, generation phases, and first 11×11 map."""

import hashlib
import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-to-dng/handoff.json"
OUTPUT = ROOT / "build/traces/dng-generation"


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
    expected_template = (ROOT / "extracted/DNG").read_bytes()[0xA619-0x8956:0xA692-0x8956]
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"generation.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    phases = []
    timeout = None
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8956:
                    raise RuntimeError("restored DNG entry differs")
                client.ok("set-turbo 8")
                try:
                    for label, address in (("generator entry", 0x8C5D),
                                           ("template copy complete", 0x8C87),
                                           ("layout initialization complete", 0x8CBB),
                                           ("generator return", 0x8DE6)):
                        points.append(wait_at(client, label, (address,)))
                        map_bytes = client.mem(0xB099, 121)
                        phases.append({"label": label, "pc": f"0x{address:04X}",
                                       "seed_a504_a505": client.mem(0xA504, 2).hex(),
                                       "depth_a506": client.mem(0xA506, 1).hex(),
                                       "map_sha256": hashlib.sha256(map_bytes).hexdigest(),
                                       "map_hex": map_bytes.hex(),
                                       "template_match": map_bytes == expected_template})
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG generation trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "generation.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "phases": phases, "timeout": timeout,
              "template_sha256": hashlib.sha256(expected_template).hexdigest(),
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for phase in phases:
        print(f"{phase['label']}: seed={phase['seed_a504_a505']} "
              f"map_sha256={phase['map_sha256'][:16]} "
              f"template_match={phase['template_match']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG generation trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
