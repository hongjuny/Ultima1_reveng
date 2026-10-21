#!/usr/bin/env python3
"""Compare first castle input with inherited or cleared final-slot padding."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/tcmaps-last-slot/handoff.json"
OUTPUT = ROOT / "build/traces/tcmaps-tail-effect"


def trial(emulator, disk, source, clear, output):
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    name = "cleared" if clear else "original"
    final = output / f"{name}.a2state"
    final.unlink(missing_ok=True)
    with (output / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x89E0:
                    raise RuntimeError("restored copy-complete PC differs")
                before = client.mem(0xB6FC, 4).hex()
                if clear:
                    client.set_mem(0xB6FC, bytes(4))
                client.ok("set-turbo 8")
                point = wait_at(client, f"{name} first input", (0x8A27, 0x88F8, 0x160D))
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                return {"intervention": None if not clear else
                        {"address": "0xB6FC", "value": "00000000"},
                        "before": before, "at_input": client.mem(0xB6FC, 4).hex(),
                        "checkpoint": point, "final_cpu": client.ok("get-cpu"),
                        "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["trials"]["last"]["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trials = {name: trial(emulator, Path(disk_item["path"]), source, clear, OUTPUT)
              for name, clear in (("original", False), ("cleared", True))}
    a = main_ram(Path(trials["original"]["snapshot"]["path"]))
    b = main_ram(Path(trials["cleared"]["snapshot"]["path"]))
    differences = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "trials": trials, "main_ram_differences":
              [f"0x{x:04X}" for x in differences]}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"CAS first input differences: {report['main_ram_differences']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TCMAPS tail-effect trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
