#!/usr/bin/env python3
"""Probe the two numeric gates on the controlled CAS princess exit path."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/cas-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/cas-princess-gate"
TRIALS = {"ace_19_xp_6500": (19, 6500),
          "ace_20_xp_6499": (20, 6499),
          "ace_20_xp_6500": (20, 6500)}


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def trial(name, ace, experience, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A27:
                    raise RuntimeError("source is not at CAS first input")
                initial = {"edge_tile": client.mem(0xB6BD, 1)[0],
                           "ace": client.mem(0x7EB6, 1)[0],
                           "experience": int.from_bytes(client.mem(0x7EE7, 2), "little"),
                           "request": client.mem(0x7EB5, 1)[0]}
                if initial["edge_tile"] < 5 or initial["request"] != 0:
                    raise RuntimeError(f"unsuitable castle source: {initial}")
                client.set_mem(0xB6BD, b"\x04")
                client.set_mem(0x7EB6, bytes((ace,)))
                client.set_mem(0x7EE7, experience.to_bytes(2, "little"))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8AC1")
                client.ok("key 8")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8AC1:
                    raise RuntimeError(f"princess branch not reached: {cpu}")
                points = [{"label": "controlled princess exit", "pc": "0x8AC1",
                           "cpu": cpu, "state": client.ok("get-state")}]
                original = client.mem(0x8AC1, 3)
                if original != bytes.fromhex("20 1e 84"):
                    raise RuntimeError(f"unexpected narrative call bytes: {original.hex()}")
                # Skip only the long narrative/presentation block. The original
                # reward calculation and both qualification comparisons remain.
                client.set_mem(0x8AC1, bytes.fromhex("4c 38 8b"))
                points.append(wait_at(client, "qualification check", (0x8B65,)))
                adjusted_xp = int.from_bytes(client.mem(0x7EE7, 2), "little")
                points.append(wait_at(client, "qualification result", (0x8B78, 0x8B7B)))
                qualified = points[-1]["pc"] == "0x8B7B"
                if qualified:
                    points.append(wait_at(client, "craft request write", (0x8BF5,)))
                points.append(wait_at(client, "castle exit", (0x8BFA,)))
                return {"controlled": {"edge_tile": {"before": initial["edge_tile"],
                                                       "after": 4},
                                       "narrative_skip": {"address": "$8AC1",
                                                          "before": original.hex(),
                                                          "after": "4c388b",
                                                          "target": "$8B38"},
                                       "ace": {"before": initial["ace"], "after": ace},
                                       "experience": {"before": initial["experience"],
                                                      "after": experience}},
                        "adjusted_experience": adjusted_xp,
                        "qualified": qualified,
                        "request_at_exit": client.mem(0x7EB5, 1)[0],
                        "checkpoints": points,
                        "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source is not CAS first input")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = checked(source), checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, (ace, experience) in TRIALS.items():
        result = trial(name, ace, experience, emulator, disk, snapshot, Ctl)
        results[name] = result
        print(f"{name}: xp after reward={result['adjusted_experience']}, "
              f"qualified={result['qualified']}, "
              f"request={result['request_at_exit']}", flush=True)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "trials": results}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"CAS princess gate trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
