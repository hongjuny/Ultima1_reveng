#!/usr/bin/env python3
"""Break inside SPA I/V/Z before their long display and delay sequences."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_spa_command_survey import SOURCE, OUTPUT, checked
from trace_startup import cpu_pc, wait_at


STAGES = {
    "i": (ord("I"), (0x90D5, 0x90DE, 0x911F)),
    "v": (ord("V"), (0x9298, 0x92D5, 0x935B)),
    "z": (ord("Z"), (0x91C3, 0x85A2)),
}


def run(name, key, addresses, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"{name}-stages.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("snapshot PC is not SPA input")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok(f"key {key}")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8A62 or int(cpu.split(" a=")[1][:2], 16) != key:
                    raise RuntimeError(f"unexpected key return: {cpu}")
                points = [{"label": "key return", "pc": "0x8A62", "cpu": cpu}]
                for index, address in enumerate(addresses):
                    points.append(wait_at(client, f"{name} stage {index}", (address,)))
                return {"key": key, "checkpoints": points,
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
    runs = {name: run(name, key, addresses, emulator, disk, snapshot, Ctl)
            for name, (key, addresses) in STAGES.items()}
    report = {"source_snapshot": prior["snapshot"], "working_game_disk": disk_item,
              "runs": runs}
    path = OUTPUT / "stages.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"SPA long-command stages failed: {error}", file=sys.stderr)
        raise SystemExit(1)
