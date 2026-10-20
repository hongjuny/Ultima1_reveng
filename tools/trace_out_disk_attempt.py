#!/usr/bin/env python3
"""Observe the OUT disk fallback result and STUPH loader return."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-ram-attempt" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-disk-attempt"


def pathname(client) -> str:
    count = client.mem(0xBA79, 1)[0]
    if count > 63:
        return f"invalid length {count}"
    return client.mem(0xBA7A, count).decode("ascii", errors="replace")


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("disk-fallback snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"disk-result.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x16B9:
                    raise RuntimeError("snapshot is not at OUT disk fallback")
                if client.mem(0x1709, 4) != b"OUT\x00":
                    raise RuntimeError("disk fallback filename is not relative OUT")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "OUT disk read return", (0x16C8,)))
                    print(f"disk read: carry={status_carry(points[-1]['cpu'])} "
                          f"path={pathname(client)!r} {points[-1]['cpu']}", flush=True)
                    points.append(wait_at(client, "loader result", (0x16FC,)))
                    print(f"loader result: carry={status_carry(points[-1]['cpu'])} "
                          f"{points[-1]['cpu']}", flush=True)
                    points.append(wait_at(client, "OUT load caller return", (0x892B,)))
                    print(f"caller return: carry={status_carry(points[-1]['cpu'])} "
                          f"{points[-1]['cpu']}", flush=True)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"disk fallback stopped before expected return: {timeout}",
                          flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
                final_path = pathname(client)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "disk-result.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "final_cpu": final_cpu, "final_state": final_state,
              "final_path": final_path,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private probe: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT disk-attempt trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
