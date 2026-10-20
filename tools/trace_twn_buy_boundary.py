#!/usr/bin/env python3
"""Replay one food-pack purchase with controlled Coin values 4 and 5."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "twn-buy-prompt" / "handoff.json"
BASE = ROOT / "build" / "traces"


def watched(client) -> dict:
    return {"coin": list(client.mem(0x7ED4, 2)),
            "food": list(client.mem(0x7EE5, 2)),
            "quantity_aa69": list(client.mem(0xAA69, 2)),
            "cost_72": list(client.mem(0x72, 2))}


def replay(coin: int) -> int:
    if coin not in (4, 5):
        raise ValueError("boundary replay accepts only Coin=4 or 5")
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

    output = BASE / f"twn-buy-boundary-{coin}"
    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"boundary.pending-{os.getpid()}.a2state"
    pre_pending = output / f"before.pending-{os.getpid()}.a2state"
    post_pending = output / f"after.pending-{os.getpid()}.a2state"
    for path in (pending, pre_pending, post_pending):
        path.unlink(missing_ok=True)
    points = []
    timeout = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0xA2F9 or \
                        client.mem(0x7ED4, 2) != bytes((100, 0)):
                    raise RuntimeError("restored purchase state differs")
                client.ok(f"save-state {pre_pending}")
                wait_for_snapshot(pre_pending)
                client.set_mem(0x7ED4, bytes((coin,)))
                client.ok(f"save-state {post_pending}")
                wait_for_snapshot(post_pending)
                before = watched(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $A392")
                client.ok("key 49")
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
                    point = wait_at(client, "cost computed", (0x932F,))
                    point["watched"] = watched(client)
                    points.append(point)
                    point = wait_at(client, "funds decision", (0x933B, 0x933E))
                    point["watched"] = watched(client)
                    points.append(point)
                    expected = 0x933B if coin == 4 else 0x933E
                    if cpu_pc(point["cpu"]) != expected:
                        raise RuntimeError(f"Coin={coin} selected unexpected branch")
                    next_addr = 0x9236 if coin == 4 else 0x9362
                    point = wait_at(client, "branch outcome", (next_addr,))
                    point["watched"] = watched(client)
                    points.append(point)
                    point = wait_at(client, "next town input", (0x8A1E,))
                    point["watched"] = watched(client)
                    points.append(point)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"TWN Coin={coin} boundary stopped: {timeout}", flush=True)
                after = watched(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "boundary.a2state"
    pending.replace(final)
    pre = output / "before.a2state"
    post = output / "after.a2state"
    pre_pending.replace(pre)
    post_pending.replace(post)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "controlled_change": {"address": "0x7ED4", "before": 100, "after": coin},
              "intervention_snapshots": {
                  "before": {"path": str(pre), **describe(pre)},
                  "after": {"path": str(post), **describe(post)}},
              "input": {"digits": "1", "terminator": 13},
              "checkpoints": points, "timeout": timeout,
              "before": before, "after": after, "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Coin={coin}: {before} → {after}; branch={points[3]['pc']}; private trace: {path}")
    return 0 if timeout is None else 1


def main() -> int:
    for coin in (4, 5):
        if replay(coin):
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, IndexError) as error:
        print(f"TWN buy boundary failed: {error}", file=sys.stderr)
        raise SystemExit(1)
