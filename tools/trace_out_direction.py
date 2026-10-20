#!/usr/bin/env python3
"""Replay one outdoor direction key through dispatch and the next input poll."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-first-input" / "handoff.json"
DIRECTION_KEYS = (0x0B, 0x0A, 0x15, 0x08)


def changes(before: bytes, after: bytes, base: int) -> dict:
    return {f"${base + offset:04X}": [old, new]
            for offset, (old, new) in enumerate(zip(before, after)) if old != new}


def main(key: int = 0x0B, source_report: Path = SOURCE,
         output: Path | None = None) -> int:
    if key not in DIRECTION_KEYS:
        raise ValueError(f"not one of the four direction keys: {key}")
    if output is None:
        output = ROOT / "build" / "traces" / f"out-direction-{key:02x}"
    expected_index = DIRECTION_KEYS.index(key) * 2
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source trace is not at outdoor input")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
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
    handler = None
    command_index = None
    tile_lookup = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("restored PC differs")
                before = client.mem(0x7E00, 0x200)
                before_zp = client.mem(0x00, 0x80)
                if client.mem(0x7E53 + expected_index // 2, 1)[0] != key:
                    raise RuntimeError("direction key differs in live command table")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A74")
                client.ok(f"key {key}")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8A74 or int(cpu.split(" a=")[1][:2], 16) != key:
                        raise RuntimeError(f"direction key did not return from poll: {cpu}")
                    points.append({"label": "poll return", "pc": "0x8A74",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    points.append(wait_at(client, "command path", (0x89CB,)))
                    points.append(wait_at(client, "command lookup return", (0x89CE,)))
                    cpu = points[-1]["cpu"]
                    command_index = int(cpu.split(" x=")[1][:2], 16)
                    if command_index != expected_index:
                        raise RuntimeError(f"direction mapped to unexpected index {command_index}")
                    points.append(wait_at(client, "handler selection", (0x89D0, 0x89DF)))
                    if points[-1]["pc"] != "0x89D0":
                        raise RuntimeError("direction key was not dispatched")
                    pointer = client.mem(0x9AAA + command_index, 2)
                    handler = pointer[0] | pointer[1] << 8
                    points.append(wait_at(client, "patched handler call", (0x89DC,)))
                    if client.mem(0x89DC, 3) != bytes((0x20, *pointer)):
                        raise RuntimeError("handler call did not match pointer table")
                    points.append(wait_at(client, "direction handler", (handler,)))
                    points.append(wait_at(client, "tile lookup", (0x99D1,)))
                    points.append(wait_at(client, "tile byte ready", (0x99F6,)))
                    cpu = points[-1]["cpu"]
                    raw_tile = int(cpu.split(" a=")[1][:2], 16)
                    tile_x = int(cpu.split(" x=")[1][:2], 16)
                    tile_y = int(cpu.split(" y=")[1][:2], 16)
                    pointer = client.mem(0x72, 2)
                    tile_address = pointer[0] | pointer[1] << 8
                    tile_address += tile_x
                    if client.mem(tile_address, 1)[0] != raw_tile:
                        raise RuntimeError("tile lookup did not read the computed map byte")
                    client.ok("step-instruction")
                    shifted_cpu = client.ok("get-cpu")
                    if cpu_pc(shifted_cpu) != 0x99F7:
                        raise RuntimeError(f"tile decode did not reach RTS: {shifted_cpu}")
                    tile_code = int(shifted_cpu.split(" a=")[1][:2], 16)
                    if tile_code != raw_tile >> 1:
                        raise RuntimeError("tile decode was not a right shift")
                    tile_lookup = {"x": tile_x, "y": tile_y,
                                   "address": tile_address, "raw": raw_tile,
                                   "code": tile_code}
                    points.append(wait_at(client, "handler return", (0x89DF,)))
                    points.append(wait_at(client, "next outdoor frame", (0x8995, 0x89E8)))
                    if points[-1]["pc"] == "0x8995":
                        points.append(wait_at(client, "next main loop", (0x89A1,)))
                        points.append(wait_at(client, "next key poll", (0x8A6C, 0x89E8)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"OUT direction replay stopped: {timeout}", flush=True)
                after = client.mem(0x7E00, 0x200)
                after_zp = client.mem(0x00, 0x80)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / f"direction-{key:02x}.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": key, "at_pc": "0x8A6C"},
              "command_index": command_index, "handler": handler,
              "tile_lookup": tile_lookup,
              "checkpoints": points, "timeout": timeout,
              "state_changes": changes(before, after, 0x7E00),
              "zero_page_changes": changes(before_zp, after_zp, 0),
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    if handler is not None:
        print(f"handler=${handler:04X} index={command_index} PC=${cpu_pc(final_cpu):04X}")
    if tile_lookup is not None:
        print(f"tile lookup: {tile_lookup}")
    print(f"state changes: {report['state_changes']}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT direction trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
