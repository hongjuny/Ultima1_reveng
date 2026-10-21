#!/usr/bin/env python3
"""Compare the $05/$06 generator draw on first entry and level-one return."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


CASES = (
    ("initial", ROOT / "build/traces/out-to-dng/handoff.json", 0x8956),
    ("return1", ROOT / "build/traces/dng-stairs-k/handoff.json", 0x8DDA),
)


def trace_case(label: str, source_report: Path, expected_pc: int) -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != expected_pc:
        raise RuntimeError(f"{label}: source PC differs")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    output = ROOT / f"build/traces/dng-random-tile-{label}"
    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"random-tile.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    draw = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != expected_pc:
                    raise RuntimeError(f"{label}: restored PC differs")
                client.ok("set-turbo 8")
                if expected_pc == 0x8DDA:
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $8DE4")
                    client.ok("key 75")
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8DE4 or " a=4B " not in cpu:
                        raise RuntimeError(f"{label}: K poll did not return: {cpu}")
                    points.append({"label": "K poll return", "pc": "0x8DE4",
                                   "cpu": cpu, "state": client.ok("get-state")})
                try:
                    points.append(wait_at(client, "random tile draw returned", (0x8D23,)))
                    cpu = points[-1]["cpu"]
                    random_byte = int(cpu.split(" a=")[1][:2], 16)
                    x, y = client.mem(0xA4EE, 2)
                    draw = {"random_byte": random_byte, "target_x": x, "target_y": y,
                            "predicted_tile": 5 + (random_byte & 1),
                            "depth": client.mem(0xA506, 1).hex()}
                    points.append(wait_at(client, "random tile loop complete", (0x8D36,)))
                    draw["tile_after_loop"] = client.mem(0xB099 + 11*y + x, 1)[0]
                    points.append(wait_at(client, "first dungeon key poll", (0x8DDA,)))
                    draw["tile_at_poll"] = client.mem(0xB099 + 11*y + x, 1)[0]
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"{label} tile draw stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "random-tile.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "draw": draw, "timeout": timeout,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{label}: {draw}; private trace: {path}")
    return 0 if timeout is None else 1


def main() -> int:
    for label, source, pc in CASES:
        if trace_case(label, source, pc):
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG random tile trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
