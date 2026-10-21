#!/usr/bin/env python3
"""Follow the castle's left-edge exit through OUT reload and coordinate restore."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "cas-exit-left" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-to-out"


def main(source_report: Path = SOURCE, output: Path = OUTPUT,
         death_path: bool = False, expected_coords: str = "1e1f") -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x88FD:
        raise RuntimeError("source trace is not at module selector")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    expected = (ROOT / "extracted" / "OUT").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"out.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    filename = None
    memory_match = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x88FD or " a=04 " not in client.ok("get-cpu"):
                    raise RuntimeError("restored OUT selector differs")
                saved_coords = client.mem(0x7E73, 2).hex()
                if saved_coords != expected_coords:
                    raise RuntimeError("outdoor coordinates were not retained")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "OUT request", (0x8920,)))
                    filename = client.mem(0x7E16, 8).split(b"\x00", 1)[0].decode("ascii")
                    if filename != "OUT":
                        raise RuntimeError(f"selector filename is {filename!r}")
                    points.append(wait_at(client, "OUT loader return", (0x892B,)))
                    cpu = points[-1]["cpu"]
                    if int(cpu.split(" p=")[1][:2], 16) & 1:
                        raise RuntimeError(f"OUT load returned carry set: {cpu}")
                    memory_match = client.mem(0x8956, len(expected)) == expected
                    if not memory_match:
                        raise RuntimeError("OUT overlay differs from extracted file")
                    points.append(wait_at(client, "OUT entry", (0x8956,)))
                    if death_path:
                        for label, address in (("OUT health check", 0x898A),
                                               ("OUT death reset", 0x89E8),
                                               ("health fill", 0x8A3A),
                                               ("food fill", 0x8A47),
                                               ("OUT after reset", 0x8995)):
                            point = wait_at(client, label, (address,))
                            point["position"] = list(client.mem(0, 2))
                            point["health"] = list(client.mem(0x7EC6, 2))
                            point["food"] = list(client.mem(0x7EE5, 2))
                            points.append(point)
                    points.append(wait_at(client, "OUT main loop", (0x89A1,)))
                    points.append(wait_at(client, "OUT input", (0x8A6C,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS-to-OUT trace stopped: {timeout}", flush=True)
                coords_after = client.mem(0x00, 2).hex()
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "out-input.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "saved_coords_7E73": saved_coords, "coords_after": coords_after,
              "filename": filename, "out_bytes": len(expected),
              "memory_match_at_load": memory_match,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, UnicodeError) as error:
        print(f"CAS-to-OUT trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
