#!/usr/bin/env python3
"""Replay TM's two-key attack; optional HP override is a controlled probe."""

import argparse
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-gem-command/handoff.json"


def main(mondain_hp=None, output=None, gem_destroyed=None):
    output = output or ROOT / ("build/traces/tm-attack-direction-control" if
                              mondain_hp is not None else "build/traces/tm-attack-direction")
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9815:
        raise RuntimeError("source is not at TM input")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    output.mkdir(parents=True, exist_ok=True)
    final = output / "result.a2state"
    final.unlink(missing_ok=True)
    checkpoints = []
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9815:
                    raise RuntimeError("restored TM input differs")
                before = {"player_hp": int.from_bytes(client.mem(0x7EC6, 2), "little"),
                          "mondain_hp": int.from_bytes(client.mem(0x7EF4, 2), "little"),
                          "gem_destroyed": client.mem(0x95AB, 1)[0],
                          "position": list(client.mem(0, 2))}
                if mondain_hp is not None:
                    if not 0 < mondain_hp < 0x8000:
                        raise ValueError("Mondain HP override must be 1..32767")
                    client.set_mem(0x7EF4, mondain_hp.to_bytes(2, "little"))
                if gem_destroyed is not None:
                    if gem_destroyed not in (0, 1):
                        raise ValueError("gem override must be 0 or 1")
                    client.set_mem(0x95AB, bytes((gem_destroyed,)))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8EDC")
                client.ok("key 65")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8EDC:
                    raise RuntimeError("A did not reach TM attack handler")
                checkpoints.append({"label": "attack handler", "pc": "0x8EDC",
                                    "cpu": client.ok("get-cpu")})
                checkpoints.append(wait_at(client, "direction input", (0x9815,)))
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $9177")
                client.ok("key 21")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x9177:
                    raise RuntimeError("east did not reach TM direction decoder")
                checkpoints.append({"label": "east decoded", "pc": "0x9177",
                                    "cpu": client.ok("get-cpu")})
                checkpoints.append(wait_at(client, "attack result", (0x8F80, 0x8F73, 0x8F19)))
                result_pc = checkpoints[-1]["pc"]
                if result_pc == "0x8F80":
                    checkpoints.append(wait_at(client, "damage applied", (0x8FEE, 0x8FC8, 0x8FD6, 0x8FED)))
                    if checkpoints[-1]["pc"] == "0x8FEE":
                        checkpoints.append(wait_at(client, "ending gate", (0x9034, 0x9033, 0x8FED)))
                after = {"player_hp": int.from_bytes(client.mem(0x7EC6, 2), "little"),
                         "mondain_hp": int.from_bytes(client.mem(0x7EF4, 2), "little"),
                         "gem_destroyed": client.mem(0x95AB, 1)[0],
                         "phase": client.mem(0x7EF2, 1)[0],
                         "position": list(client.mem(0, 2))}
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "intervention": {"mondain_hp": mondain_hp,
                                           "gem_destroyed": gem_destroyed},
                          "input": [65, 21], "before": before, "after": after,
                          "checkpoints": checkpoints,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (output / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM A east: {before} → {after}; {[p['pc'] for p in checkpoints]}", flush=True)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--mondain-hp", type=int)
        parser.add_argument("--gem-destroyed", type=int, choices=(0, 1))
        parser.add_argument("--output", type=Path)
        args = parser.parse_args()
        main(args.mondain_hp, args.output, args.gem_destroyed)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM directional attack failed: {error}", file=sys.stderr)
        raise SystemExit(1)
