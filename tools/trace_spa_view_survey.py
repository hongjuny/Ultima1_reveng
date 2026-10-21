#!/usr/bin/env python3
"""Probe the remaining distinct keys in SPA's nested V view."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_spa_command_survey import OUTPUT, checked, sample, changes
from trace_startup import cpu_pc, wait_at


COMMANDS = {
    "default_a": (ord("A"), 0x97EE),
    "f": (ord("F"), 0x964D),
    "i": (ord("I"), 0x98F2),
    "r": (ord("R"), 0x98F5),
    "v": (ord("V"), 0x98FE),
    "z": (ord("Z"), 0x99FE),
    "ctrl_a": (1, 0x8845),
    "n": (ord("N"), 0x885B),
}


def trial(name, key, target, emulator, disk, snapshot, Ctl):
    with (OUTPUT / f"view-survey-{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError(f"{name}: SPA source PC changed")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok("key 86")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A62:
                    raise RuntimeError(f"{name}: V key not returned")
                points = [wait_at(client, f"{name} V entry", (0x9298,)),
                          wait_at(client, f"{name} view poll", (0x9361,))]
                before = sample(client)
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $93B5")
                client.ok(f"key {key}")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x93B5:
                    raise RuntimeError(f"{name}: nested key did not decode")
                points.append({"label": f"{name} nested decode", "pc": "0x93B5",
                               "cpu": client.ok("get-cpu")})
                points.append(wait_at(client, f"{name} patched subcommand", (0x93D8,)))
                actual = int.from_bytes(client.mem(0x93D9, 2), "little")
                if actual != target:
                    raise RuntimeError(f"{name}: target ${actual:04X} != ${target:04X}")
                points.append(wait_at(client, f"{name} handler", (target,)))
                entered = sample(client)
                boundary = None
                timeout = None
                try:
                    points.append(wait_at(client, f"{name} next boundary",
                                          (0x93DB, 0x9361, 0x8A5F, 0x88FB)))
                    boundary = points[-1]["pc"]
                except RuntimeError as error:
                    timeout = str(error)
                after = sample(client)
                return {"key": key, "target": f"${target:04X}",
                        "points": points, "boundary": boundary,
                        "timeout": timeout, "on_entry": changes(before, entered),
                        "after": changes(before, after),
                        "final_cpu": client.ok("get-cpu")}
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    stages = json.loads((OUTPUT / "stages.json").read_text())
    source, disk_item = stages["source_snapshot"], stages["working_game_disk"]
    snapshot, disk = checked(source), checked(disk_item)
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    runs = {}
    for name, (key, target) in COMMANDS.items():
        runs[name] = trial(name, key, target, emulator, disk, snapshot, Ctl)
        run = runs[name]
        print(name, run["target"], "→", run["boundary"] or "pending",
              "player", run["after"]["player"]["addresses"],
              "spa", run["after"]["spa"]["addresses"], flush=True)
    path = OUTPUT / "view-survey.json"
    path.write_text(json.dumps({"source_snapshot": source,
                                "working_game_disk": disk_item,
                                "runs": runs}, indent=2) + "\n")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"SPA view survey failed: {error}", file=sys.stderr)
        raise SystemExit(1)
