#!/usr/bin/env python3
"""Replay CAS → OUT with only the castle craft-request byte controlled."""

import json
from pathlib import Path
import re
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/cas-exit-left/handoff.json"
OUTPUT = ROOT / "build/traces/final-craft-spawn"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x88FD:
        raise RuntimeError("source did not reach the OUT selector")
    snapshot, disk = checked(prior["snapshot"]), checked(prior["working_game_disk"])
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x88FD:
                    raise RuntimeError("restored selector differs")
                initial = {"request": client.mem(0x7EB5, 1)[0],
                           "limit": client.mem(0x7EA8, 1)[0],
                           "object_count": client.mem(0x7EF6, 1)[0]}
                if initial["request"] != 0 or initial["limit"] >= 7:
                    raise RuntimeError(f"source unsuitable: {initial}")
                client.set_mem(0x7EB5, b"\x01")
                client.ok("set-turbo 8")
                points = [wait_at(client, "OUT entry", (0x8956,)),
                          wait_at(client, "craft request gate", (0x9567,))]
                if client.mem(0x7EB5, 1) != b"\x01":
                    raise RuntimeError("request was not retained through OUT entry")
                points.append(wait_at(client, "craft placement", (0x958C,)))
                cpu = points[-1]["cpu"]
                x = int(re.search(r"\bx=([0-9A-F]{2})\b", cpu).group(1), 16)
                y = int(re.search(r"\by=([0-9A-F]{2})\b", cpu).group(1), 16)
                cell = 0x6000 + y * 64 + x
                before = client.mem(cell, 1)[0]
                points.append(wait_at(client, "world-object writer", (0x9927,)))
                points.append(wait_at(client, "request reset", (0x9591,)))
                points.append(wait_at(client, "request cleared", (0x9596,)))
                after = client.mem(cell, 1)[0]
                request_after = client.mem(0x7EB5, 1)[0]
                objects_after = client.mem(0x7EF6, 1)[0]
                points.append(wait_at(client, "next OUT input", (0x8A6C,)))
                current_map = client.mem(cell, 1)[0]
                path = OUTPUT / "first-input.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "intervention": {"address": "0x7EB5", "before": 0, "after": 1},
                          "initial": initial, "checkpoints": points,
                          "placement": {"x": x, "y": y, "address": cell,
                                        "raw_before": before, "raw_after": after,
                                        "raw_at_poll": current_map,
                                        "request_after": request_after,
                                        "objects_after": objects_after},
                          "snapshot": {"path": str(path), **describe(path)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"final craft: {report['placement']}")
    print(f"private trace: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"final craft trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
