#!/usr/bin/env python3
"""Test the odd castle quest producer at a real dungeon kill boundary."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-attack-repeat-3/poll/handoff.json"
OUTPUT = ROOT / "build/traces/dng-odd-quest"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
        raise RuntimeError("source does not stop at dungeon input")
    snapshot, disk = checked(prior["snapshot"]), checked(prior["working_game_disk"])
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8DDA:
                    raise RuntimeError("restored dungeon poll differs")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DE4")
                client.ok("key 65")  # Ordinary lethal A attack
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8DE4:
                    raise RuntimeError("A did not return from dungeon poll")
                points = [wait_at(client, "defeated monster reward", (0x94A7,))]
                before = {"type": client.mem(0xA52E, 1)[0],
                          "depth": client.mem(0xA506, 1)[0],
                          "quest": list(client.mem(0x7EA9, 8))}
                if before != {"type": 1, "depth": 1, "quest": [0] * 8}:
                    raise RuntimeError(f"kill boundary differs: {before}")
                client.set_mem(0xA52E, b"\x05")
                client.set_mem(0xA506, b"\x03")
                client.set_mem(0x7EAA, b"\x01")
                points.append(wait_at(client, "odd quest write", (0x94C3,)))
                points.append(wait_at(client, "odd quest write complete", (0x94C6,)))
                after = {"type": client.mem(0xA52E, 1)[0],
                         "depth": client.mem(0xA506, 1)[0],
                         "quest": list(client.mem(0x7EA9, 8))}
                path = OUTPUT / "completed.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "input": 65,
                          "interventions": [{"address": "0xA52E", "before": 1, "after": 5},
                                            {"address": "0xA506", "before": 1, "after": 3},
                                            {"address": "0x7EAA", "before": 0, "after": 1}],
                          "before": before, "after": after,
                          "checkpoints": points,
                          "snapshot": {"path": str(path), **describe(path)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"odd quest: {before} → {after}")
    print(f"private trace: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"dungeon odd quest trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
