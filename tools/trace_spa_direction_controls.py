#!/usr/bin/env python3
"""Replay four SPA direction keys independently from one private first poll."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-board-transitions/probe.json"
OUTPUT = ROOT / "build/traces/spa-direction-controls"
KEYS = {"up": (11, 0x8FAD, 5), "down": (10, 0x900E, 5),
        "right": (21, 0x904E, 2), "left": (8, 0x9074, 2)}


def read_state(client):
    return {f"${address:04X}": client.mem(address, 1)[0]
            for address in (0x923E, 0x923F, 0x9240, 0x928A, 0x928B,
                            0x928E, 0x7EE9, 0x7EEA, 0x7EEB, 0x7EEC)}


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def trial(name, key, handler, cost, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError(f"{name}: snapshot is not at SPA input")
                initial = read_state(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok(f"key {key}")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8A62 or f" a={key:02X} " not in cpu:
                    raise RuntimeError(f"{name}: key return differs: {cpu}")
                points = [{"label": "key return", "pc": "0x8A62", "cpu": cpu}]
                points.append(wait_at(client, f"{name} decode", (0x8A6A,)))
                points.append(wait_at(client, f"{name} patched jump", (0x8AB0,)))
                actual = int.from_bytes(client.mem(0x8AB1, 2), "little")
                if actual != handler:
                    raise RuntimeError(f"{name}: handler ${actual:04X} != ${handler:04X}")
                points.append(wait_at(client, f"{name} handler", (handler,)))
                points.append(wait_at(client, f"{name} fuel service", (0xA154,)))
                before_debit = read_state(client)
                if f" a={cost:02X} " not in points[-1]["cpu"]:
                    raise RuntimeError(f"{name}: unexpected fuel cost")
                points.append(wait_at(client, f"{name} fuel service exit", (0xA1BA,)))
                after_debit = read_state(client)
                points.append(wait_at(client, f"{name} next input", (0x8A5F,)))
                final = read_state(client)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    return {"key": key, "handler": f"${handler:04X}", "cost": cost,
            "checkpoints": points, "initial": initial,
            "before_debit": before_debit, "after_debit": after_debit,
            "next_input": final, "final_cpu": final_cpu}


def main():
    prior = json.loads(SOURCE.read_text())["spa"]
    snapshot = checked(prior["snapshot"])
    disk_item = json.loads((ROOT / "build/traces/out-first-input/handoff.json").read_text())["working_game_disk"]
    disk = checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs = {name: trial(name, *args, emulator, disk, snapshot, Ctl)
            for name, args in KEYS.items()}
    report = {"source_snapshot": prior["snapshot"],
              "working_game_disk": disk_item, "runs": runs}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for name, run in runs.items():
        print(name, run["before_debit"], "→", run["after_debit"], flush=True)
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"SPA direction trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
