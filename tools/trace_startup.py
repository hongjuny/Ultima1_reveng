#!/usr/bin/env python3
"""Trace U1.SYSTEM's handoff into U1.INTRO from a private boot snapshot."""

import json
import os
from pathlib import Path
import re
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_pc, wait_for_snapshot
from disassemble import ROOT


OUTPUT = ROOT / "build" / "traces" / "startup"


def cpu_pc(cpu: str) -> int:
    match = re.search(r"\bpc=([0-9A-Fa-f]{4})\b", cpu)
    if not match:
        raise RuntimeError(f"a2m did not return a PC: {cpu}")
    return int(match.group(1), 16)


def wait_at(client, label: str, candidates: tuple[int, ...]) -> dict:
    client.ok_or_data("break-clear-all")
    for address in candidates:
        client.ok_or_data(f"break-exec ${address:04X}")
    client.ok("run")
    try:
        client.ok("wait-paused 15000")
    except RuntimeError as error:
        try:
            client.ok("pause")
            client.ok("wait-paused 3000")
        except RuntimeError:
            pass
        cpu = client.ok("get-cpu")
        state = client.ok("get-state")
        raise RuntimeError(f"{label}: no breakpoint hit; {cpu}; {state}") from error
    cpu = client.ok("get-cpu")
    address = cpu_pc(cpu)
    if address not in candidates:
        state = client.ok("get-state")
        raise RuntimeError(f"{label}: unexpected stop at ${address:04X}; {cpu}; {state}")
    state = client.ok("get-state")
    print(f"{label}: ${address:04X} {cpu}", flush=True)
    return {"label": label, "pc": f"0x{address:04X}", "cpu": cpu, "state": state}


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
    snapshot = OUTPUT / f"intro-entry.pending-{os.getpid()}.a2state"
    snapshot.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {boot_path}")
                wait_for_pc(client)
                state = client.ok("get-state")
                if "state=paused" not in state:
                    raise RuntimeError(f"snapshot load did not leave the CPU paused: {state}")
                instruction = client.mem(0x2088, 2)
                if instruction[0] != 0x78:
                    raise RuntimeError(f"expected SEI at $2088 after restore, got {instruction.hex()}")
                client.ok_or_data("break-clear-all")
                client.ok("step-instruction")
                client.ok("wait-paused 3000")
                stepped = client.ok("get-cpu")
                if cpu_pc(stepped) != 0x2089:
                    raise RuntimeError(f"stepping SEI did not reach $2089: {stepped}")
                print(f"restored and stepped $2088: {stepped}", flush=True)
                checkpoints.append(wait_at(client, "U1.SYSTEM setup complete", (0x21A0,)))
                branch = wait_at(client, "startup-file decision", (0x21D3, 0x21D6))
                checkpoints.append(branch)
                header = client.mem(0x2000, 16)
                low_memory = client.mem(0x0100, 0x40)
                branch["header_2000_200F_hex"] = header.hex()
                branch["low_memory_0100_013F_hex"] = low_memory.hex()
                print(f"$2000 header: {header.hex(' ')}", flush=True)
                print(f"$0100-$013F: {low_memory.hex(' ')}", flush=True)
                if branch["pc"] == "0x21D3":
                    raise RuntimeError(
                        f"U1.SYSTEM took the no-startup-file branch at $21D3; "
                        f"$2006=${header[6]:02X}, header={header.hex()}"
                    )
                checkpoints.append(wait_at(client, "U1.SYSTEM exit", (0x2220,)))
                checkpoints.append(wait_at(client, "low-memory transfer", (0x0136,)))
                entry = wait_at(client, "U1.INTRO entry", (0x0800, 0x0803))
                checkpoints.append(entry)
                actual = client.mem(0x0800, 16)
                expected = (ROOT / "extracted" / "U1.INTRO").read_bytes()[:16]
                if actual != expected:
                    raise RuntimeError("memory at $0800 differs from U1.INTRO extraction")
                entry["memory_matches_extraction"] = True
                entry_pc = int(entry["pc"], 16)
                branch = 0x0F23 if entry_pc == 0x0800 else 0x0F41
                checkpoints.append(wait_at(client, "U1.INTRO branch", (branch,)))
                client.ok(f"save-state {snapshot}")
                wait_for_snapshot(snapshot)
            finally:
                client.s.close()
        finally:
            stop(process)

    if not snapshot.is_file() or snapshot.stat().st_size == 0:
        raise RuntimeError("a2m did not write the intro snapshot")
    final_snapshot = OUTPUT / "intro-entry.a2state"
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
