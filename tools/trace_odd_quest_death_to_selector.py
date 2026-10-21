#!/usr/bin/env python3
"""Follow the completed-quest dungeon death to the OUT overlay selector."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/odd-quest-death-probe-2/event/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-death-selector"


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["state"]["event"] != "death" or cpu_pc(prior["final_cpu"]) != 0x98DD:
        raise RuntimeError("source is not at dungeon death handler")
    snapshot_item, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(snapshot_item["path"]), Path(disk_item["path"])
    for item, path in ((snapshot_item, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "selector.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x98DD:
                    raise RuntimeError("restored dungeon death differs")
                client.ok("set-turbo 8")
                points = [wait_at(client, "death return", (0x88F8,)),
                          wait_at(client, "module selector", (0x88FD,))]
                if " a=04 " not in points[-1]["cpu"]:
                    raise RuntimeError("death did not select OUT")
                state = {"quest": list(client.mem(0x7EA9, 8)),
                         "gems": list(client.mem(0x7E75, 4)),
                         "hp": list(client.mem(0x7EC6, 2)),
                         "outdoor_position": list(client.mem(0x7E73, 2))}
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": snapshot_item,
                          "working_game_disk": disk_item,
                          "checkpoints": points, "timeout": None,
                          "state": state, "final_cpu": client.ok("get-cpu"),
                          "final_state": client.ok("get-state"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"dungeon death selected OUT: {state}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest death selector failed: {error}", file=sys.stderr)
        raise SystemExit(1)
