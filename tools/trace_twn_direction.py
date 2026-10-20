#!/usr/bin/env python3
"""Replay one town movement key and capture the next town input."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


TRACE = ROOT / "build" / "traces"
FIRST_INPUT = TRACE / "twn-first-input" / "handoff.json"
KEYS = (0x0B, 0x0A, 0x15, 0x08)


def main(key: int = 0x0B, source_report: Path = FIRST_INPUT,
         output: Path | None = None) -> int:
    if key not in KEYS:
        raise ValueError(f"not a town direction key: ${key:02X}")
    if output is None:
        output = TRACE / f"twn-direction-{key:02x}"
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A1E:
        raise RuntimeError("source trace is not at town input")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"direction.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A1E:
                    raise RuntimeError("restored town poll differs")
                before = list(client.mem(0, 2))
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A26")
                client.ok(f"key {key}")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A26 or f" a={key:02X} " not in cpu:
                        raise RuntimeError(f"direction key did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A26", "cpu": cpu})
                    points.append(wait_at(client, "command lookup return", (0x8A41,)))
                    if f" x={KEYS.index(key) * 2:02X} " not in points[-1]["cpu"]:
                        raise RuntimeError("direction mapped to unexpected index")
                    points.append(wait_at(client, "tile collision check", (0xA26F,)))
                    points.append(wait_at(client, "next town input", (0x8A1E,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"TWN direction ${key:02X} stopped: {timeout}", flush=True)
                after = list(client.mem(0, 2))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / f"direction-{key:02x}.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": key, "at_pc": "0x8A1E"},
              "checkpoints": points, "timeout": timeout,
              "position_before": before, "position_after": after,
              "final_cpu": final_cpu, "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"town movement ${key:02X}: {before} → {after}; private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN direction trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
