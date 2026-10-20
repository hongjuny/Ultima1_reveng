#!/usr/bin/env python3
"""Press T while standing on the verified code-$66 town food shop."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "twn-to-food-shop" / "step-10" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "twn-shop-menu"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A1E:
        raise RuntimeError("source trace is not at town key poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"shop.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A1E or \
                        client.mem(0, 2) != bytes((23, 11)):
                    raise RuntimeError("restored food-shop position differs")
                before = {"coin": list(client.mem(0x7ED4, 2)),
                          "food": list(client.mem(0x7EE5, 2))}
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A26")
                client.ok("key 84")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A26 or " a=54 " not in cpu:
                        raise RuntimeError(f"T did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A26", "cpu": cpu})
                    points.append(wait_at(client, "trade command lookup", (0x8A41,)))
                    if " x=2A " not in points[-1]["cpu"]:
                        raise RuntimeError("T command index differs")
                    points.append(wait_at(client, "trade handler", (0x9093,)))
                    points.append(wait_at(client, "shop tile lookup", (0x90B5,)))
                    points.append(wait_at(client, "Buy/Sell menu", (0x90F0,)))
                    shop_index = client.mem(0x72, 1)[0]
                    points.append(wait_at(client, "shop choice input", (0x8A1E,)))
                except RuntimeError as error:
                    timeout = str(error)
                    shop_index = None
                    print(f"TWN shop menu stopped: {timeout}", flush=True)
                after = {"coin": list(client.mem(0x7ED4, 2)),
                         "food": list(client.mem(0x7EE5, 2))}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "shop-menu.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": 84, "at_pc": "0x8A1E"},
              "checkpoints": points, "timeout": timeout, "shop_index": shop_index,
              "before": before, "after": after, "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"shop index={shop_index}; watched: {before} → {after}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN shop menu failed: {error}", file=sys.stderr)
        raise SystemExit(1)
