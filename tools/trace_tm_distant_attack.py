#!/usr/bin/env python3
"""Observe TM's distant Mondain attack from the blocked pursuit state."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from trace_tm_phase_transition import state


SOURCE = ROOT / "build/traces/tm-phase1-return/handoff.json"
OUTPUT = ROOT / "build/traces/tm-distant-attack"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9815:
        raise RuntimeError("source is not at TM input")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "after-attack.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9815:
                    raise RuntimeError("restored TM input differs")
                client.ok("set-turbo 8")
                turns = []
                for number in range(1, 31):
                    before = state(client)
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $99E7")
                    client.ok_or_data("break-exec $9815")
                    client.ok("key 32")
                    client.ok("wait-paused 15000")
                    entry = cpu_pc(client.ok("get-cpu"))
                    if entry not in (0x99E7, 0x9815):
                        raise RuntimeError(f"turn {number}: unexpected PC ${entry:04X}")
                    at_entry = state(client)
                    if entry == 0x99E7:
                        boundary = wait_at(client, f"turn {number} after distant attack",
                                           (0x9815, 0x88F8, 0x160D))["pc"]
                    else:
                        boundary = "0x9815"
                    after = state(client)
                    turns.append({"number": number, "input": 32, "before": before,
                                  "entry_pc": f"0x{entry:04X}", "at_entry": at_entry,
                                  "after": after, "boundary_pc": boundary})
                    print(f"turn {number}: entry ${entry:04X} player "
                          f"{before['player_hp']}→{after['player_hp']}", flush=True)
                    if (entry == 0x99E7 and after["player_hp"] < before["player_hp"]) or boundary != "0x9815":
                        break
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "turns": turns, "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM distant attack: {len(turns)} turns", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM distant attack trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
