#!/usr/bin/env python3
"""Probe TM's blocked-flee regeneration at the 500-HP phase boundary."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-phase-transition/handoff.json"
OUTPUT = ROOT / "build/traces/tm-regen-boundary"


def state(client):
    return {"player_hp": int.from_bytes(client.mem(0x7EC6, 2), "little"),
            "mondain_hp": int.from_bytes(client.mem(0x7EF4, 2), "little"),
            "phase": client.mem(0x7EF2, 1)[0],
            "player_position": list(client.mem(0, 2)),
            "mondain_position": list(client.mem(0xB628, 2))}


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["pre_regen_snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    require_turn = prior["turns"][39]
    if require_turn["number"] != 40 or require_turn["after"]["mondain_hp"] != 482:
        raise RuntimeError("source turn 40 differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trials = {}
    for label, hp in (("original", None), ("hp-495", 495)):
        out = OUTPUT / label
        out.mkdir(parents=True, exist_ok=True)
        final = out / "next-input.a2state"
        final.unlink(missing_ok=True)
        with (out / "a2m.log").open("w") as log:
            process = launch(emulator, Path(disk_item["path"]), None, log)
            try:
                client = connect(Ctl, process)
                try:
                    client.ok("hello")
                    client.ok("wait-paused 3000")
                    client.ok(f"load-state {source['path']}")
                    if cpu_pc(client.ok("get-cpu")) != 0x9815:
                        raise RuntimeError("restored TM phase-two input differs")
                    before = state(client)
                    if hp is not None:
                        client.set_mem(0x7EF4, hp.to_bytes(2, "little"))
                    client.ok("set-turbo 8")
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $8EA2")
                    client.ok("key 11")
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) != 0x8EA2:
                        raise RuntimeError("up move did not return")
                    points = [wait_at(client, "next TM loop", (0x8E5E,)),
                              wait_at(client, "next TM input", (0x9815,))]
                    after = state(client)
                    client.ok(f"save-state {final}")
                    wait_for_snapshot(final)
                    time.sleep(0.2)
                    trials[label] = {"intervention": None if hp is None else
                                     {"address": "0x7EF4", "mondain_hp": hp},
                                     "input": 11, "before": before, "after": after,
                                     "checkpoints": points,
                                     "final_cpu": client.ok("get-cpu"),
                                     "snapshot": {"path": str(final), **describe(final)}}
                finally:
                    client.s.close()
            finally:
                stop(process)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "trials": trials}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM regen boundary: {[(k, v['after']) for k, v in trials.items()]}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM regen boundary failed: {error}", file=sys.stderr)
        raise SystemExit(1)
