#!/usr/bin/env python3
"""Trace the post-NIF finale animation to its final key wait."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-nif-copy/handoff.json"
OUTPUT = ROOT / "build/traces/tm-final-wait"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["final_cpu"]) != 0x9094:
        raise RuntimeError("source is not after NIF copy")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "final-wait.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9094:
                    raise RuntimeError("restored TM animation differs")
                client.ok("set-turbo 8")
                points = [wait_at(client, "animation loop", (0x90AA,)),
                          wait_at(client, "final key wait", (0x9132,))]
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $914D")
                client.ok("key 32")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x914D:
                    raise RuntimeError("final key did not reach $914D")
                points.append({"label": "final key loop jump", "pc": "0x914D",
                               "cpu": client.ok("get-cpu")})
                points.append(wait_at(client, "final wait again", (0x912F,)))
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "input": 32, "checkpoints": points,
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM final wait: {[p['pc'] for p in points]}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM final wait trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
