#!/usr/bin/env python3
"""Probe every food-price tier boundary with a one-byte attribute change."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "twn-shop-menu" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "twn-price-tiers"
VALUES = (19, 20, 39, 40, 59, 60, 79, 80)


def price_for(attribute: int) -> int:
    return max(1, 5 - attribute // 20)


def replay(attribute: int) -> dict:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A1E:
        raise RuntimeError("source trace is not at shop choice input")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    output = OUTPUT / f"attribute-{attribute:03d}"
    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"tier.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A1E or \
                        client.mem(0x7ED2, 1) != b"\x0f":
                    raise RuntimeError("restored food-price attribute differs")
                client.ok(f"save-state {pre_pending}")
                wait_for_snapshot(pre_pending)
                client.set_mem(0x7ED2, bytes((attribute,)))
                client.ok(f"save-state {post_pending}")
                wait_for_snapshot(post_pending)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A26")
                client.ok("key 66")
                try:
                    client.ok("wait-paused 15000")
                    if cpu_pc(client.ok("get-cpu")) != 0x8A26 or \
                            " a=42 " not in client.ok("get-cpu"):
                        raise RuntimeError("B did not return from poll")
                    points.append({"label": "poll return", "pc": "0x8A26",
                                   "cpu": client.ok("get-cpu")})
                    points.append(wait_at(client, "food price entry", (0x9257,)))
                    points.append(wait_at(client, "food price ready", (0x926F,)))
                    price = client.mem(0xAA6B, 1)[0]
                    prompt_digit = client.mem(0x928A, 1)[0]
                    if price != price_for(attribute) or prompt_digit != 0x30 + price:
                        raise RuntimeError(f"attribute {attribute} computed unexpected price {price}")
                except RuntimeError as error:
                    timeout = str(error)
                    price = None
                    prompt_digit = None
                    print(f"TWN attribute={attribute} stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "price.a2state"
    pending.replace(final)
    pre = output / "before.a2state"
    post = output / "after.a2state"
    pre_pending.replace(pre)
    post_pending.replace(post)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "controlled_change": {"address": "0x7ED2", "before": 15,
                                    "after": attribute},
              "intervention_snapshots": {
                  "before": {"path": str(pre), **describe(pre)},
                  "after": {"path": str(post), **describe(post)}},
              "input": {"key_ascii": 66, "at_pc": "0x8A1E"},
              "checkpoints": points, "timeout": timeout,
              "price": price, "prompt_digit": prompt_digit,
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"attribute {attribute}: price {price}; private trace: {path}")
    return report


def main() -> int:
    for attribute in VALUES:
        if replay(attribute)["timeout"] is not None:
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN food-price tiers failed: {error}", file=sys.stderr)
        raise SystemExit(1)
