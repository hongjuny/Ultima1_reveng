#!/usr/bin/env python3
"""Measure cycles between speaker accesses for two controlled STUPH effects."""

import json
from pathlib import Path
import re
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_spa_direction_controls import SOURCE, checked
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build/traces/stuph-sound-pulses"
EFFECTS = {"0E": (0x1B32, 16), "10": (0x1B42, 50)}
CYCLES = re.compile(r"\bcycles=(\d+)")


def trial(name, entry, count, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("source is not the SPA first input")
                expected = (ROOT / "extracted/STUPH").read_bytes()[0x1B32-0x0800:0x1B48-0x0800]
                if client.mem(0x1B32, len(expected)) != expected:
                    raise RuntimeError("resident STUPH effect differs from extracted file")
                source_cpu = client.ok("get-cpu")
                client.ok(f"set-reg pc ${entry:04X}")
                client.ok("set-turbo 8")
                hits = []
                for n in range(count + 1):
                    point = wait_at(client, f"sound {name} event {n}", (0x1B3A, 0x1B41))
                    pc = cpu_pc(point["cpu"])
                    match = CYCLES.search(point["cpu"])
                    if not match:
                        raise RuntimeError("CPU cycle counter missing")
                    if pc != (0x1B3A if n < count else 0x1B41):
                        raise RuntimeError(f"sound {name}: unexpected PC ${pc:04X} at event {n}")
                    hits.append({"pc": f"${pc:04X}", "cycles": int(match.group(1))})
            finally:
                client.s.close()
        finally:
            stop(process)
    return {"entry": f"${entry:04X}", "source_cpu": source_cpu,
            "speaker_accesses": count, "hits": hits,
            "intervals": [b["cycles"]-a["cycles"] for a,b in zip(hits,hits[1:])],
            "injected_pc": True}


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
    runs = {name: trial(name, *config, emulator, disk, snapshot, Ctl)
            for name, config in EFFECTS.items()}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps({"source_snapshot": source,
                                "working_game_disk": disk_item,
                                "runs": runs}, indent=2) + "\n")
    for name, run in runs.items():
        print(name, "accesses", run["speaker_accesses"],
              "intervals", run["intervals"], flush=True)
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"STUPH sound pulse trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
