#!/usr/bin/env python3
"""Choose Buy at the food shop and capture its numeric input entry."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "twn-shop-menu" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "twn-buy-prompt"


def main() -> int:
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A1E:
                    raise RuntimeError("restored shop choice differs")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A26")
                client.ok("key 66")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A26 or " a=42 " not in cpu:
                        raise RuntimeError(f"B did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A26", "cpu": cpu})
                    for label, address in (("Buy branch", 0x911E),
                                           ("patched shop call", 0x9137),
                                           ("food buy handler", 0x9257),
                                           ("quantity parser entry", 0xA2F9)):
                        points.append(wait_at(client, label, (address,)))
                    shop_price = client.mem(0xAA6B, 1)[0]
                except RuntimeError as error:
                    timeout = str(error)
                    shop_price = None
                    print(f"TWN buy prompt stopped: {timeout}", flush=True)
                watched = {"coin": list(client.mem(0x7ED4, 2)),
                           "food": list(client.mem(0x7EE5, 2))}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "buy-prompt.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": 66, "at_pc": "0x8A1E"},
              "checkpoints": points, "timeout": timeout,
              "price_per_pack": shop_price, "watched": watched,
              "final_cpu": final_cpu, "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"food pack price={shop_price}; watched={watched}; private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN buy prompt failed: {error}", file=sys.stderr)
        raise SystemExit(1)
