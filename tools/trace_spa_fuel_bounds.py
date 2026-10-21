#!/usr/bin/env python3
"""Probe SPA Up with controlled Fuel values near its five-unit cost."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_spa_direction_controls import SOURCE, checked, read_state
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build/traces/spa-fuel-bounds"
FUELS = (0, 4, 5)


def trial(fuel, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"fuel-{fuel}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("source is not SPA first input")
                before = read_state(client)
                client.set_mem(0x7EE9, fuel.to_bytes(2, "little"))
                intervened = read_state(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok("key 11")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A62:
                    raise RuntimeError("Up did not return")
                points = [wait_at(client, f"Fuel {fuel} next branch",
                                  (0x8FAD, 0x8A5F, 0x88FB))]
                if cpu_pc(points[-1]["cpu"]) == 0x8FAD:
                    points.append(wait_at(client, f"Fuel {fuel} service or input",
                                          (0xA154, 0x8A5F, 0x88FB)))
                    if cpu_pc(points[-1]["cpu"]) == 0xA154:
                        service_entry = read_state(client)
                        points.append(wait_at(client, f"Fuel {fuel} debit complete", (0xA1BA,)))
                        service_exit = read_state(client)
                        points.append(wait_at(client, f"Fuel {fuel} next input or exit",
                                              (0x8A5F, 0x88FB)))
                    else:
                        service_entry = service_exit = None
                else:
                    service_entry = service_exit = None
                final = read_state(client)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    return {"fuel": fuel, "original": before, "intervened": intervened,
            "points": points, "service_entry": service_entry,
            "service_exit": service_exit, "final": final, "final_cpu": final_cpu}


def main():
    prior = json.loads(SOURCE.read_text())["spa"]
    source = prior["snapshot"]
    snapshot = checked(source)
    disk_item = json.loads((ROOT / "build/traces/out-first-input/handoff.json").read_text())["working_game_disk"]
    disk = checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs = {str(fuel): trial(fuel, emulator, disk, snapshot, Ctl) for fuel in FUELS}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps({"source_snapshot": source,
                                "working_game_disk": disk_item,
                                "runs": runs}, indent=2) + "\n")
    for fuel, run in runs.items():
        print(fuel, [p["pc"] for p in run["points"]], run["final"], flush=True)
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"SPA Fuel boundary trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
