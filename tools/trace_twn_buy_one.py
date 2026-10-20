#!/usr/bin/env python3
"""Buy one food pack and capture the two-byte payment and food credit."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "twn-buy-prompt" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "twn-buy-one"


def watched(client) -> dict:
    return {"coin": list(client.mem(0x7ED4, 2)),
            "food": list(client.mem(0x7EE5, 2)),
            "quantity_aa69": list(client.mem(0xAA69, 2)),
            "cost_72": list(client.mem(0x72, 2))}


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0xA2F9:
        raise RuntimeError("source trace is not at quantity parser entry")
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
    pending = OUTPUT / f"buy.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0xA2F9:
                    raise RuntimeError("restored quantity parser differs")
                before = watched(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $A392")
                client.ok("key 49")  # ASCII '1'
                try:
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) != 0xA392:
                        raise RuntimeError("digit 1 was not accepted")
                    points.append({"label": "digit accepted", "pc": "0xA392",
                                   "cpu": client.ok("get-cpu"), "watched": watched(client)})
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $92E0")
                    client.ok("key 13")
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) != 0x92E0:
                        raise RuntimeError("Return did not complete quantity input")
                    points.append({"label": "quantity accepted", "pc": "0x92E0",
                                   "cpu": client.ok("get-cpu"), "watched": watched(client)})
                    for label, address in (("cost computed", 0x932F),
                                           ("payment branch", 0x933E),
                                           ("payment complete", 0x9362),
                                           ("next town input", 0x8A1E)):
                        point = wait_at(client, label, (address,))
                        point["watched"] = watched(client)
                        points.append(point)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"TWN buy one stopped: {timeout}", flush=True)
                after = watched(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "buy-one.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"digits": "1", "terminator": 13},
              "checkpoints": points, "timeout": timeout,
              "before": before, "after": after, "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    for point in points:
        print(point["label"], point["pc"], point["watched"])
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN buy one failed: {error}", file=sys.stderr)
        raise SystemExit(1)
