#!/usr/bin/env python3
"""Replay all four OUT world edges from one private input snapshot."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_out_world_boundary import SOURCE, checked, state
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build/traces/out-world-boundaries"
CASES = {
    "east": (0x000C, 0x4A, 0x9496),
    "west": (0x000C, 0xF5, 0x949F),
    "south": (0x000D, 0x4A, 0x94A8),
    "north": (0x000D, 0xF5, 0x94B4),
}


def trial(name, address, value, edge_pc, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError(f"{name}: restored PC differs")
                initial = state(client)
                map_initial = hashlib.sha256(client.mem(0x6000, 4096)).hexdigest()
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A74")
                client.ok("key 11")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8A74 or " a=0B " not in cpu:
                    raise RuntimeError(f"{name}: Up key did not return: {cpu}")
                points = [{"label": "Up returned", "pc": "0x8A74", "cpu": cpu},
                          wait_at(client, "OUT move commit", (0x9416,))]
                before = state(client)
                client.set_mem(address, bytes((value,)))
                intervened = state(client)
                points += [wait_at(client, "boundary test", (0x9477,)),
                           wait_at(client, f"{name} edge", (edge_pc,)),
                           wait_at(client, "world index mask", (0x94C1,))]
                masked = state(client)
                points.append(wait_at(client, "world bits encode", (0x9503,)))
                encoded_before = state(client)
                points.append(wait_at(client, "world map ready", (0x952C,)))
                encoded = state(client)
                map_after = hashlib.sha256(client.mem(0x6000, 4096)).hexdigest()
                points.append(wait_at(client, "OUT next input", (0x8A6C,)))
                final = state(client)
                final_cpu = client.ok("get-cpu")
                return {"patch_address": f"${address:04X}", "patch_value": value,
                        "edge_pc": f"${edge_pc:04X}", "key": 11,
                        "points": points, "initial": initial,
                        "before_intervention": before, "intervened": intervened,
                        "masked": masked, "encoded_before": encoded_before,
                        "encoded": encoded, "final": final,
                        "map_initial_sha256": map_initial,
                        "map_after_sha256": map_after, "final_cpu": final_cpu}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("OUT source is not at first input")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = checked(source), checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs = {}
    for name, case in CASES.items():
        runs[name] = trial(name, *case, emulator, disk, snapshot, Ctl)
        run = runs[name]
        print(name, f"world {run['before_intervention']['$7E6F']}→{run['final']['$7E6F']}",
              f"XY=(${run['final']['$0000']:02X},${run['final']['$0001']:02X})",
              "map changed", run["map_initial_sha256"] != run["map_after_sha256"],
              flush=True)
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps({"source_snapshot": source,
                                "working_game_disk": disk_item,
                                "runs": runs}, indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"OUT four-boundary trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
