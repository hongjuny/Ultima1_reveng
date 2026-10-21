#!/usr/bin/env python3
"""Wait through a TM combat phase and observe Mondain's movement."""

import argparse
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-phase-transition/handoff.json"
OUTPUT = ROOT / "build/traces/tm-phase2-wait"
MAX_TURNS = 80


def state(client):
    return {"player_hp": int.from_bytes(client.mem(0x7EC6, 2), "little"),
            "mondain_hp": int.from_bytes(client.mem(0x7EF4, 2), "little"),
            "phase": client.mem(0x7EF2, 1)[0],
            "player_position": list(client.mem(0, 2)),
            "mondain_position": list(client.mem(0xB628, 2))}


def main(source_report=SOURCE, output=OUTPUT, stop_mode="phase-change"):
    if stop_mode not in ("phase-change", "adjacent"):
        raise ValueError("unknown stop mode")
    prior = json.loads(source_report.read_text())
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
    output.mkdir(parents=True, exist_ok=True)
    final = output / "after-wait.a2state"
    final.unlink(missing_ok=True)
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9815:
                    raise RuntimeError("restored TM input differs")
                initial = state(client)
                client.ok("set-turbo 8")
                turns = []
                for number in range(1, MAX_TURNS + 1):
                    before = state(client)
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $8EA2")
                    client.ok("key 32")
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) != 0x8EA2:
                        raise RuntimeError(f"Space handler failed on turn {number}")
                    boundary = wait_at(client, f"wait turn {number}", (0x9815, 0x88F8, 0x160D))
                    after = state(client)
                    turns.append({"number": number, "input": 32,
                                  "before": before, "after": after,
                                  "boundary_pc": boundary["pc"]})
                    print(f"wait {number}: target {before['mondain_hp']}→"
                          f"{after['mondain_hp']} phase {after['phase']} "
                          f"{before['mondain_position']}→{after['mondain_position']} "
                          f"player {before['player_hp']}→{after['player_hp']}", flush=True)
                    adjacent = sum(abs(a - b) for a, b in zip(
                        after["player_position"], after["mondain_position"])) <= 1
                    if ((stop_mode == "phase-change" and
                         after["phase"] != initial["phase"]) or
                        (stop_mode == "adjacent" and adjacent) or
                        boundary["pc"] != "0x9815"):
                        break
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "initial": initial, "stop_mode": stop_mode, "turns": turns,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (output / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM wait: {len(turns)} turns; {turns[-1]['after']}", flush=True)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--source", type=Path, default=SOURCE)
        parser.add_argument("--output", type=Path, default=OUTPUT)
        parser.add_argument("--stop-mode", choices=("phase-change", "adjacent"),
                            default="phase-change")
        args = parser.parse_args()
        main(args.source, args.output, args.stop_mode)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM phase-two wait failed: {error}", file=sys.stderr)
        raise SystemExit(1)
