#!/usr/bin/env python3
"""Observe whether a completed dungeon quest survives the death path."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_dng_key_w import main as press_key
from trace_startup import cpu_pc


SOURCE = ROOT / "build/traces/odd-quest-return/level3-attack-02/poll/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-death-probe"


def main(source_report: Path = SOURCE, output: Path = OUTPUT):
    key_path = output / "space"
    if press_key(32, key_path, source_report):
        raise RuntimeError("Space command failed")
    prior = json.loads((key_path / "handoff.json").read_text())
    snapshot_item, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(snapshot_item["path"]), Path(disk_item["path"])
    for item, path in ((snapshot_item, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    event_output = output / "event"
    event_output.mkdir(parents=True, exist_ok=True)
    final = event_output / "event.a2state"
    final.unlink(missing_ok=True)
    with (event_output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8E0E:
                    raise RuntimeError("handler return differs")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DDA")
                client.ok_or_data("break-exec $98DD")
                client.ok("run")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                pc = cpu_pc(cpu)
                if pc not in (0x8DDA, 0x98DD):
                    raise RuntimeError(f"unexpected post-command event: {cpu}")
                state = {"event": "death" if pc == 0x98DD else "dungeon_poll",
                         "hp": list(client.mem(0x7EC6, 2)),
                         "quest": list(client.mem(0x7EA9, 8)),
                         "depth": client.mem(0xA506, 1)[0],
                         "position": list(client.mem(0xA4E8, 2))}
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": snapshot_item,
                          "working_game_disk": disk_item, "cpu": cpu,
                          "timeout": None, "final_cpu": cpu,
                          "state": state, "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    path = event_output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"completed quest post-command event: {state}")
    print(f"private trace: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest death probe failed: {error}", file=sys.stderr)
        raise SystemExit(1)
