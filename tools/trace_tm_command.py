#!/usr/bin/env python3
"""Replay one TM command and capture its state at the next input."""

import argparse
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-intro-pages/probe.json"
OUTPUT = ROOT / "build/traces/tm-command"
WATCH = (0, 1, 0x7EC6, 0x7EC7, 0x7EF2, 0x7EF4, 0x7EF5,
         0x95AB, 0xB62A, 0xB62B, 0xB628, 0xB629)


def state(client):
    return {f"${address:04X}": client.mem(address, 1)[0] for address in WATCH}


def main(key: int, source_report: Path = SOURCE, output: Path = OUTPUT) -> int:
    prior = json.loads(source_report.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    disk_item = prior.get("working_game_disk") or json.loads(
        (ROOT / "build/traces/out-first-input/handoff.json").read_text())["working_game_disk"]
    disk = Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    if cpu_pc(prior["final_cpu"]) != 0x9815:
        raise RuntimeError("source is not at TM input")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    output.mkdir(parents=True, exist_ok=True)
    final = output / "next-input.a2state"
    final.unlink(missing_ok=True)
    points = []
    timeout = None
    handler = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x9815:
                    raise RuntimeError("restored TM input differs")
                before = state(client)
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8E83")
                client.ok(f"key {key}")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8E83 or f" a={key:02X} " not in cpu:
                        raise RuntimeError(f"TM key did not return: {cpu}")
                    points.append({"label": "key return", "pc": "0x8E83",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    points.append(wait_at(client, "command index", (0x8E91,)))
                    points.append(wait_at(client, "patched call", (0x8E9F,)))
                    handler = int.from_bytes(client.mem(0x8EA0, 2), "little")
                    points.append(wait_at(client, "command handler", (handler,)))
                    points.append(wait_at(client, "handler return", (0x8EA2,)))
                    points.append(wait_at(client, "next TM loop", (0x8E5E,)))
                    points.append(wait_at(client, "next TM input", (0x9815,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"TM command ${key:02X} stopped: {timeout}", flush=True)
                after = state(client)
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source,
                          "working_game_disk": disk_item,
                          "input": {"key_ascii": key, "at_pc": "0x9815"},
                          "handler": None if handler is None else f"0x{handler:04X}",
                          "checkpoints": points, "timeout": timeout,
                          "before": before, "after": after,
                          "final_cpu": client.ok("get-cpu"),
                          "final_state": client.ok("get-state"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"TM ${key:02X} handler={report['handler']} "
          f"position={before['$0000'], before['$0001']}→{after['$0000'], after['$0001']} "
          f"HP={before['$7EC6'], before['$7EC7']}→{after['$7EC6'], after['$7EC7']} "
          f"gem={before['$95AB']}→{after['$95AB']}", flush=True)
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--key", type=lambda value: int(value, 0), default=0x15)
        parser.add_argument("--source", type=Path, default=SOURCE)
        parser.add_argument("--output", type=Path, default=OUTPUT)
        args = parser.parse_args()
        raise SystemExit(main(args.key, args.source, args.output))
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM command trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
