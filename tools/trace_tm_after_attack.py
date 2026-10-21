#!/usr/bin/env python3
"""Continue a TM attack result through the next monster turn."""

import argparse
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-attack-direction/handoff.json"
OUTPUT = ROOT / "build/traces/tm-after-attack"


def state(client):
    return {"player_hp": int.from_bytes(client.mem(0x7EC6, 2), "little"),
            "mondain_hp": int.from_bytes(client.mem(0x7EF4, 2), "little"),
            "phase": client.mem(0x7EF2, 1)[0],
            "gem_destroyed": client.mem(0x95AB, 1)[0],
            "player_position": list(client.mem(0, 2)),
            "mondain_position": list(client.mem(0xB628, 2))}


def main(source_report=SOURCE, output=OUTPUT):
    prior = json.loads(source_report.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) not in (0x8FC8, 0x8F73):
        raise RuntimeError("source is not after a TM attack result")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    output.mkdir(parents=True, exist_ok=True)
    final = output / "next-input.a2state"
    final.unlink(missing_ok=True)
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) not in (0x8FC8, 0x8F73):
                    raise RuntimeError("restored TM attack result differs")
                before = state(client)
                client.ok("set-turbo 8")
                points = [wait_at(client, "attack handler return", (0x8EA2,)),
                          wait_at(client, "next TM loop", (0x8E5E,)),
                          wait_at(client, "next TM input or death", (0x9815, 0x88F8, 0x160D))]
                after = state(client)
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "checkpoints": points, "before": before, "after": after,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (output / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM first hit aftermath: {before} → {after}", flush=True)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--source", type=Path, default=SOURCE)
        parser.add_argument("--output", type=Path, default=OUTPUT)
        args = parser.parse_args()
        main(args.source, args.output)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM attack aftermath failed: {error}", file=sys.stderr)
        raise SystemExit(1)
