#!/usr/bin/env python3
"""Follow a Space key through SPA command dispatch and one complete loop."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from trace_turn_contracts import diff, sample


SOURCE = ROOT / "build/traces/out-board-transitions/probe.json"
OUTPUT = ROOT / "build/traces/spa-first-key"


def main():
    prior = json.loads(SOURCE.read_text())["spa"]
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("SPA first-input snapshot differs")
    disk_item = json.loads((ROOT / "build/traces/out-first-input/handoff.json").read_text())["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working disk differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A5F:
                    raise RuntimeError("SPA input PC differs")
                before = sample(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A62")
                client.ok("key 32")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8A62 or " a=20 " not in cpu:
                    raise RuntimeError(f"SPA Space did not return: {cpu}")
                points.append({"label": "Space returned", "pc": "0x8A62", "cpu": cpu})
                points.append(wait_at(client, "SPA shared decode result", (0x8A6A,)))
                if " x=08 " not in points[-1]["cpu"]:
                    raise RuntimeError("SPA Space index differs")
                points.append(wait_at(client, "SPA handler selection", (0x8AA4,)))
                points.append(wait_at(client, "SPA patched jump", (0x8AB0,)))
                target = int.from_bytes(client.mem(0x8AB1, 2), "little")
                points.append(wait_at(client, "SPA Space handler", (target,)))
                points.append(wait_at(client, "SPA post-command", (0x8AB3,)))
                points.append(wait_at(client, "SPA next loop", (0x8A53,)))
                points.append(wait_at(client, "SPA next input", (0x8A5F,)))
                after = sample(client)
                final = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    result = {"source_snapshot_sha256": source["sha256"], "key": 32,
              "handler": f"${target:04X}", "checkpoints": points,
              "player": diff(before["player"], after["player"], 0x7E00),
              "zero_page": diff(before["zero_page"], after["zero_page"], 0),
              "video": diff(before["video"], after["video"], 0x2000),
              "initial_frame": before["frame"], "final_frame": after["frame"],
              "final_cpu": final}
    path = OUTPUT / "probe.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"SPA Space handler {result['handler']}; player changed {result['player']['addresses']}; "
          f"next poll ${cpu_pc(final):04X}")
    print(f"private report: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"SPA first key trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
