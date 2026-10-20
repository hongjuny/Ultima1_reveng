#!/usr/bin/env python3
"""Observe STUPH's /RAM/OUT attempt and its fallback decision."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-loader-probe" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-ram-attempt"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("OUT loader-stage snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs from probe")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"ram-result.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x16AD:
                    raise RuntimeError("snapshot is not at /RAM/OUT call")
                if client.mem(0x1703, 10) != b"\x80/RAM/OUT\x00":
                    raise RuntimeError("RAM-disk lookup path differs")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "RAM lookup return", (0x16B2,)))
                    carry = status_carry(points[-1]["cpu"])
                    print(f"RAM lookup: carry={carry} {points[-1]['cpu']}", flush=True)
                    if carry:
                        points.append(wait_at(client, "disk fallback", (0x16B9,)))
                        print(f"disk fallback call: {points[-1]['cpu']}", flush=True)
                    else:
                        points.append(wait_at(client, "RAM success path", (0x16FC,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"lookup paused before return: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "ram-result.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private probe: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT RAM-attempt trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
