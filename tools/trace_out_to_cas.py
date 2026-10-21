#!/usr/bin/env python3
"""Follow the verified tile-$04 selector through the CAS overlay load."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-enter-04" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-to-cas"


def main(source_report: Path = SOURCE, output: Path = OUTPUT) -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x88FD:
        raise RuntimeError("source trace did not reach common selector")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    expected = (ROOT / "extracted" / "CAS").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"cas.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x88FD or " a=10 " not in client.ok("get-cpu"):
                    raise RuntimeError("restored selector differs")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "CAS request", (0x8920,)))
                    filename = client.mem(0x7E16, 8).split(b"\x00", 1)[0].decode("ascii")
                    if filename != "CAS":
                        raise RuntimeError(f"selector filename is {filename!r}")
                    points.append(wait_at(client, "CAS loader return", (0x892B,)))
                    cpu = points[-1]["cpu"]
                    flags = int(cpu.split(" p=")[1][:2], 16)
                    if flags & 1:
                        raise RuntimeError(f"CAS load returned carry set: {cpu}")
                    memory_match = client.mem(0x8956, len(expected)) == expected
                    if not memory_match:
                        raise RuntimeError("CAS overlay differs from extracted file")
                    points.append(wait_at(client, "CAS entry", (0x8956,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"OUT-to-CAS trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "cas-entry.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout, "filename": filename,
              "cas_bytes": len(expected), "memory_match": memory_match,
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
        print(f"OUT-to-CAS trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
