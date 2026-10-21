#!/usr/bin/env python3
"""Replay SPA front-view directions and H from one private view poll."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_spa_command_survey import OUTPUT, checked
from trace_startup import cpu_pc, wait_at


COMMANDS = {"space": (32, 0x95BF, None), "up": (11, 0x9617, None),
            "down": (10, 0x9632, None), "right": (21, 0x95FC, None),
            "left": (8, 0x95E1, None), "h": (ord("H"), 0x97F9, None),
            "h_fuel99": (ord("H"), 0x97F9, 104),
            "h_fuel100": (ord("H"), 0x97F9, 105)}


def state(client):
    return {f"${address:04X}": client.mem(address, 1)[0]
            for address in (0x0000, 0x0001, 0x006C, 0x006D,
                            0x923E, 0x923F, 0x9240, 0x928A, 0x928B,
                            0x93F9, 0x93FA, 0x00BA, 0x00BB, 0x00BC,
                            0x7EE9, 0x7EEA, 0x7EEB, 0x7EEC)}


def trial(name, key, target, start_fuel, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"view-{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("snapshot PC is not SPA input")
                if start_fuel is not None:
                    client.set_mem(0x7EE9, start_fuel.to_bytes(2, "little"))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok("key 86")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A62:
                    raise RuntimeError("V key did not return")
                points = [wait_at(client, f"{name} V command", (0x9298,)),
                          wait_at(client, f"{name} first view poll", (0x9361,))]
                initial = state(client)
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $93B5")
                client.ok(f"key {key}")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x93B5:
                    raise RuntimeError(f"{name}: nested key did not reach decode")
                points += [{"label": f"{name} nested decode", "pc": "0x93B5",
                            "cpu": client.ok("get-cpu")},
                           wait_at(client, f"{name} patched subcommand", (0x93D8,))]
                actual = int.from_bytes(client.mem(0x93D9, 2), "little")
                if actual != target:
                    raise RuntimeError(f"{name}: target ${actual:04X} != ${target:04X}")
                points.append(wait_at(client, f"{name} handler", (target,)))
                entered = state(client)
                if name == "h_fuel100":
                    points.append(wait_at(client, "H cost-100 debit", (0xA154,)))
                    debit_entry = state(client)
                    points.append(wait_at(client, "H cost-100 debit exit", (0xA1BA,)))
                    debit_exit = state(client)
                    return {"key": key, "target": f"${target:04X}",
                            "start_fuel": start_fuel, "checkpoints": points,
                            "initial": initial, "entered": entered,
                            "debit_entry": debit_entry, "debit_exit": debit_exit,
                            "next_input": None, "timeout": None,
                            "final_cpu": client.ok("get-cpu")}
                completed = None
                timeout = None
                try:
                    points.append(wait_at(client, f"{name} return", (0x93DB,)))
                    points.append(wait_at(client, f"{name} next view poll", (0x9361,)))
                    completed = state(client)
                except RuntimeError as error:
                    timeout = str(error)
                return {"key": key, "target": f"${target:04X}",
                        "start_fuel": start_fuel,
                        "checkpoints": points, "initial": initial,
                        "entered": entered, "next_input": completed,
                        "timeout": timeout, "final_state": state(client),
                        "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    stages = json.loads((OUTPUT / "stages.json").read_text())
    source = stages["source_snapshot"]
    snapshot = checked(source)
    disk_item = stages["working_game_disk"]
    disk = checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    runs = {}
    for name, (key, target, start_fuel) in COMMANDS.items():
        runs[name] = trial(name, key, target, start_fuel,
                           emulator, disk, snapshot, Ctl)
        item = runs[name]
        last = (item.get("next_input") or item.get("debit_exit") or
                item.get("final_state") or item["entered"])
        print(name, item["target"], "next", bool(item["next_input"]),
              "fuel", item["initial"]["$7EE9"], "→", last["$7EE9"],
              flush=True)
    path = OUTPUT / "view-controls.json"
    path.write_text(json.dumps({"source_snapshot": source,
                                "working_game_disk": disk_item, "runs": runs},
                               indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"SPA view controls failed: {error}", file=sys.stderr)
        raise SystemExit(1)
