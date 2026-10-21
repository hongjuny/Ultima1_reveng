#!/usr/bin/env python3
"""Follow one TM Space command from its natural first input point."""

import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from trace_turn_contracts import diff, sample


SOURCE = ROOT / "build/traces/tm-intro-pages/probe.json"
OUTPUT = ROOT / "build/traces/tm-first-key"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("TM first-input snapshot differs")
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
                if cpu_pc(client.ok("get-cpu")) != 0x9815:
                    raise RuntimeError("TM input PC differs")
                before = sample(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8E83")
                client.ok("key 32")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8E83 or " a=20 " not in cpu:
                    raise RuntimeError(f"TM Space did not return: {cpu}")
                points.append({"label": "Space returned", "pc": "0x8E83", "cpu": cpu})
                points.append(wait_at(client, "TM shared decode result", (0x8E91,)))
                if " x=08 " not in points[-1]["cpu"]:
                    raise RuntimeError("TM Space index differs")
                points.append(wait_at(client, "TM patched handler call", (0x8E9F,)))
                target = int.from_bytes(client.mem(0x8EA0, 2), "little")
                points.append(wait_at(client, "TM Space handler", (target,)))
                points.append(wait_at(client, "TM handler return", (0x8EA2,)))
                points.append(wait_at(client, "TM next loop", (0x8E5E,)))
                points.append(wait_at(client, "TM next input", (0x9815,)))
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
    print(f"TM Space handler {result['handler']}; player changed {result['player']['addresses']}; "
          f"next input ${cpu_pc(final):04X}")
    print(f"private report: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TM first key trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
