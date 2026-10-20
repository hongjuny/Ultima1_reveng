#!/usr/bin/env python3
"""Trace the first U1.SYSTEM to U1.INTRO handoff in private a2m state."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_pc, wait_for_snapshot
from disassemble import ROOT


OUTPUT = ROOT / "build" / "traces" / "startup"
TARGETS = (0x0800, 0x0F23)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    runtime = manifest["runtime"]
    boot = runtime["boot_snapshot"]
    if boot is None:
        raise RuntimeError("boot snapshot missing; run tools/capture_boot.py first")
    boot_path = Path(boot["path"])
    if describe(boot_path)["sha256"] != boot["sha256"]:
        raise RuntimeError("boot snapshot differs from baseline")
    disk = Path(manifest["disk_image"]["path"])
    emulator = Path(runtime["emulator"]["path"])
    source = ROOT / "build" / "emulator" / "a2m"
    sys.path.insert(0, str(source / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    snapshot = OUTPUT / f"intro-0F23.pending-{os.getpid()}.a2state"
    snapshot.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, boot_path, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                wait_for_pc(client)
                client.ok_or_data("break-clear-all")
                for address in TARGETS:
                    client.ok_or_data(f"break-exec ${address:04X}")
                for address in TARGETS:
                    client.ok("run")
                    client.ok("wait-paused 30000")
                    cpu = client.ok("get-cpu")
                    expected_pc = f"pc={address:04X}"
                    if expected_pc not in cpu:
                        raise RuntimeError(f"expected ${address:04X}, got {cpu}")
                    actual = client.mem(address, 16)
                    expected = (ROOT / "extracted" / "U1.INTRO").read_bytes()[address-0x0800:address-0x0800+16]
                    if actual != expected:
                        raise RuntimeError(f"memory at ${address:04X} differs from U1.INTRO extraction")
                    state = client.ok("get-state")
                    checkpoints.append({"pc": f"0x{address:04X}", "cpu": cpu,
                                        "state": state, "memory_matches_extraction": True})
                    print(f"reached U1.INTRO ${address:04X}: {cpu}", flush=True)
                client.ok(f"save-state {snapshot}")
                wait_for_snapshot(snapshot)
            finally:
                client.s.close()
        finally:
            stop(process)

    if not snapshot.is_file() or snapshot.stat().st_size == 0:
        raise RuntimeError("a2m did not write the intro snapshot")
    final_snapshot = OUTPUT / "intro-0F23.a2state"
    snapshot.replace(final_snapshot)
    snapshot = final_snapshot
    report = {"source_snapshot": str(boot_path), "checkpoints": checkpoints,
              "snapshot": {"path": str(snapshot), **describe(snapshot)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"startup trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
