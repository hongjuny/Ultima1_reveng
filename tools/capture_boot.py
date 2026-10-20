#!/usr/bin/env python3
"""Capture a private a2m boot breakpoint and verify snapshot restoration."""

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

from baseline import MANIFEST, describe
from disassemble import ROOT


BOOT_PC = "2088"
PORT = 20000 + os.getpid() % 30000
OUTPUT = ROOT / "build" / "baseline"


def connect(client_type, process):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("a2m exited before its control port opened; see build/baseline/a2m.log")
        try:
            return client_type(port=PORT, timeout=25)
        except (ConnectionRefusedError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError("a2m control port did not open; see build/baseline/a2m.log")


def require_pc(reply):
    if reply[0] != "ok":
        raise RuntimeError(f"get-cpu failed: {reply}")
    match = re.search(r"\bpc=([0-9A-Fa-f]{4})\b", reply[1])
    if not match or match.group(1).upper() != BOOT_PC:
        raise RuntimeError(f"expected PC=${BOOT_PC}, got {reply[1]}")
    return reply[1]


def launch(executable: Path, disk: Path, snapshot: Path | None, log):
    command = [str(executable), "--headless", f"--control-port={PORT}",
               "--noini", "--nosaveini", "--model=enh",
               f"--disk={disk}", "--log-level=warn"]
    if snapshot is not None:
        command.append(f"--sna={snapshot}")
    return subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)


def stop(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def wait_for_snapshot(path: Path):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return
        time.sleep(0.1)
    raise RuntimeError("a2m did not write the boot snapshot within 10 seconds")


def wait_for_pc(client):
    deadline = time.monotonic() + 10
    last = None
    while time.monotonic() < deadline:
        last = client.cmd("get-cpu")
        try:
            return require_pc(last)
        except RuntimeError:
            time.sleep(0.1)
    raise RuntimeError(f"snapshot restore did not reach PC=${BOOT_PC}: {last}")


def main() -> int:
    if not MANIFEST.is_file():
        raise RuntimeError("capture the local baseline first")
    manifest = json.loads(MANIFEST.read_text())
    runtime = manifest.get("runtime", {})
    if not manifest.get("disk_image") or not runtime.get("emulator"):
        raise RuntimeError("baseline needs disk and a2m emulator paths")
    source = ROOT / "build" / "emulator" / "a2m"
    revision = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    disk = Path(manifest["disk_image"]["path"])
    emulator = Path(runtime["emulator"]["path"])
    if describe(disk)["sha256"] != manifest["disk_image"]["sha256"]:
        raise RuntimeError("disk differs from baseline")
    if describe(emulator)["sha256"] != runtime["emulator"]["sha256"]:
        raise RuntimeError("emulator differs from baseline")
    sys.path.insert(0, str(source / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    snapshot = OUTPUT / "boot-2088.a2state"
    log_path = OUTPUT / "a2m.log"
    with log_path.open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")  # consume headless startup pause
                client.ok_or_data(f"break-exec ${BOOT_PC}")
                client.ok("run")
                client.ok("wait-paused 20000")
                cpu = require_pc(client.cmd("get-cpu"))
                state = client.ok("get-state")
                client.ok(f"save-state {snapshot}")
                wait_for_snapshot(snapshot)
            finally:
                client.s.close()
        finally:
            stop(process)

        process = launch(emulator, disk, snapshot, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                restored_cpu = wait_for_pc(client)
            finally:
                client.s.close()
        finally:
            stop(process)

    scenario = {
        "name": "cold boot to U1.SYSTEM entry",
        "emulator_revision": revision,
        "model": "Apple //e Enhanced",
        "disk_slot": "s6d0",
        "breakpoint": "0x2088",
        "inputs": [],
        "cpu_at_breakpoint": cpu,
        "state_at_breakpoint": state,
        "cpu_after_snapshot_restore": restored_cpu,
        "snapshot": {"path": str(snapshot), **describe(snapshot)},
    }
    scenario_path = OUTPUT / "boot-2088.json"
    scenario_path.write_text(json.dumps(scenario, indent=2) + "\n")
    runtime["boot_snapshot"] = scenario["snapshot"]
    runtime["input_replay"] = {"path": str(scenario_path), "inputs": [],
                               **describe(scenario_path)}
    manifest["runtime"] = runtime
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"captured and restored U1.SYSTEM entry at ${BOOT_PC}")
    print(f"private artifacts: {snapshot}, {scenario_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"boot capture failed: {error}", file=sys.stderr)
        raise SystemExit(1)
