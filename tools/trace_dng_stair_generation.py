#!/usr/bin/env python3
"""Capture map-generation phases across observed dungeon stair transitions."""

import hashlib
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
    ("return1", ROOT / "build/traces/dng-stairs-k/handoff.json"),
)
OUTPUT = ROOT / "build/traces"
PHASES = (("generator entry", 0x8C5D),
          ("template copy complete", 0x8C87),
          ("layout complete", 0x8CBB),
          ("next dungeon loop", 0x8DE6),
          ("next dungeon key poll", 0x8DDA))


def trace_case(label: str, source_report: Path) -> int:
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
    template = (ROOT / "extracted/DNG").read_bytes()[0xA619-0x8956:0xA692-0x8956]
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    output = OUTPUT / f"dng-generation-{label}"
    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"generation.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    phases = []
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
                before = {"depth": client.mem(0xA506, 1).hex(),
                          "position": client.mem(0xA4E8, 2).hex(),
                          "facing": client.mem(0xA4EC, 2).hex()}
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DE4")
                client.ok("key 75")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8DE4 or " a=4B " not in cpu:
                        raise RuntimeError(f"{label}: K did not return from poll: {cpu}")
                    checkpoints.append({"label": "K poll return", "pc": "0x8DE4",
                                        "cpu": cpu, "state": client.ok("get-state")})
                    for phase_label, address in PHASES:
                        checkpoints.append(wait_at(client, phase_label, (address,)))
                        grid = client.mem(0xB099, 121)
                        phases.append({"label": phase_label, "pc": f"0x{address:04X}",
                                       "depth": client.mem(0xA506, 1).hex(),
                                       "seed": client.mem(0xA504, 2).hex(),
                                       "position": client.mem(0xA4E8, 2).hex(),
                                       "map_sha256": hashlib.sha256(grid).hexdigest(),
                                       "map_hex": grid.hex(),
                                       "template_match": grid == template})
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"{label} generation stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "generation.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "before": before, "checkpoints": checkpoints, "phases": phases,
              "template_sha256": hashlib.sha256(template).hexdigest(),
              "timeout": timeout, "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for phase in phases:
        print(f"{label} {phase['label']}: depth={phase['depth']} seed={phase['seed']} "
              f"map={phase['map_sha256'][:16]} template={phase['template_match']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


def main() -> int:
    for label, source in CASES:
        if trace_case(label, source):
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG stair generation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
