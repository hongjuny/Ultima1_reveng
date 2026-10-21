#!/usr/bin/env python3
"""Replay SPA's remaining distinct command targets from one private poll state."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from trace_turn_contracts import diff


SOURCE = ROOT / "build/traces/out-board-transitions/probe.json"
OUTPUT = ROOT / "build/traces/spa-command-survey"
COMMANDS = {
    "ctrl_a": (1, 0x9213),
    "h": (ord("H"), 0x909A),
    "i": (ord("I"), 0x90D5),
    "n": (ord("N"), 0x91BD),
    "v": (ord("V"), 0x9298),
    "z": (ord("Z"), 0x91C3),
}


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def sample(client):
    frame = client.get_frame()
    return {
        "player": client.mem(0x7E00, 0x200),
        "spa": client.mem(0x923E, 0x5B),
        "video": client.mem(0x2000, 0x4000, "main"),
        "frame": {"number": frame["frame"],
                  "sha256": hashlib.sha256(frame["pixels"]).hexdigest()},
    }


def changes(before, after):
    return {"player": diff(before["player"], after["player"], 0x7E00),
            "spa": diff(before["spa"], after["spa"], 0x923E),
            "video": diff(before["video"], after["video"], 0x2000),
            "frame": after["frame"]}


def trial(name, key, target, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("snapshot PC is not SPA input")
                before = sample(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok(f"key {key}")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8A62 or int(cpu.split(" a=")[1][:2], 16) != key:
                    raise RuntimeError(f"unexpected key return: {cpu}")
                points = [{"label": "key return", "pc": "0x8A62", "cpu": cpu}]
                points.append(wait_at(client, f"{name} patched jump", (0x8AB0,)))
                actual = int.from_bytes(client.mem(0x8AB1, 2), "little")
                if actual != target:
                    raise RuntimeError(f"target ${actual:04X} != ${target:04X}")
                points.append(wait_at(client, f"{name} handler", (target,)))
                entered = sample(client)
                outcome = None
                error = None
                try:
                    # A command can return to the dispatcher, ask for more input,
                    # or transfer to the common overlay selector.
                    points.append(wait_at(client, f"{name} next boundary",
                                          (0x8AB3, 0x8A5F, 0x88FB)))
                    outcome = points[-1]["pc"]
                    if outcome == "0x8AB3":
                        points.append(wait_at(client, f"{name} next input",
                                              (0x8A5F, 0x88FB)))
                        outcome = points[-1]["pc"]
                except RuntimeError as exc:
                    error = str(exc)
                after = sample(client)
                return {"key": key, "target": f"${target:04X}",
                        "checkpoints": points, "boundary": outcome, "timeout": error,
                        "on_entry": changes(before, entered),
                        "after": changes(before, after),
                        "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())["spa"]
    snapshot = checked(prior["snapshot"])
    disk_item = json.loads((ROOT / "build/traces/out-first-input/handoff.json").read_text())["working_game_disk"]
    disk = checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs = {}
    for name, (key, target) in COMMANDS.items():
        runs[name] = trial(name, key, target, emulator, disk, snapshot, Ctl)
        item = runs[name]
        print(f"{name}: {item['target']} → {item['boundary'] or 'unresolved'}; "
              f"player={item['after']['player']['addresses']}; "
              f"spa={item['after']['spa']['addresses']}", flush=True)
    report = {"source_snapshot": prior["snapshot"],
              "working_game_disk": disk_item, "runs": runs}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"SPA command survey failed: {error}", file=sys.stderr)
        raise SystemExit(1)
