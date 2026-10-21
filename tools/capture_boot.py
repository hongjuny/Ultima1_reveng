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
MAX_ADDRESS_HITS = 32
MAX_STOPS = 128
PRODOS_RETURNS = {0x2173: "GET_PREFIX", 0x218C: "SET_PREFIX", 0x21A6: "READ_BLOCK"}
PRODOS_ERROR = 0x21C3
PORT = 20000 + os.getpid() % 30000
OUTPUT = ROOT / "build" / "baseline"
SOCKETPAIR_EMULATOR = ROOT / "build" / "emulator" / "a2m-socketpair-build" / "a2m"
SOCKETPAIR_CLIENTS = {}


def connect(client_type, process):
    inherited = SOCKETPAIR_CLIENTS.pop(process.pid, None)
    if inherited is not None:
        # a2m_control_client.Ctl only needs these four fields after its TCP
        # constructor. Use the already-connected socketpair endpoint instead.
        inherited.settimeout(60)
        client = client_type.__new__(client_type)
        client.s = inherited
        client.buf = b""
        client.id = 0
        client.events = []
        return client
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("a2m exited before its control port opened; see build/baseline/a2m.log")
        try:
            return client_type(port=PORT, timeout=60)
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


def launch(executable: Path, disk: Path, snapshot: Path | None, log, *, inspector=False):
    socketpair_mode = os.environ.get("ULTIMA_A2M_SOCKETPAIR") == "1"
    if socketpair_mode:
        if not SOCKETPAIR_EMULATOR.is_file():
            raise RuntimeError(
                "socketpair a2m missing; run python3 tools/build_socketpair_a2m.py"
            )
        executable = SOCKETPAIR_EMULATOR
    command = [str(executable), "--headless", f"--control-port={PORT}",
               "--noini", "--nosaveini", "--model=enh",
               f"--disk={disk}", "--log-level=warn"]
    if snapshot is not None:
        command.append(f"--sna={snapshot}")
    if inspector:
        command.append("--inspector")
    if not socketpair_mode:
        return subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    parent, child = socket.socketpair()
    try:
        environment = os.environ.copy()
        environment["A2M_CONTROL_FD"] = str(child.fileno())
        process = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, env=environment,
                                   pass_fds=(child.fileno(),))
        SOCKETPAIR_CLIENTS[process.pid] = parent
        return process
    except BaseException:
        parent.close()
        raise
    finally:
        child.close()


def stop(process):
    unused = SOCKETPAIR_CLIENTS.pop(process.pid, None)
    if unused is not None:
        unused.close()
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


def require_game_image(client, expected_header: bytes, expected_entry: bytes):
    header = client.mem(0x2000, len(expected_header))
    entry = client.mem(0x2088, len(expected_entry))
    if header != expected_header or entry != expected_entry:
        raise RuntimeError(
            f"PC=${BOOT_PC} is not U1.SYSTEM: "
            f"$2000={header.hex()} $2088={entry.hex()}"
        )
    return {"header_2000_hex": header.hex(), "entry_2088_hex": entry.hex()}


def arm_boot_breakpoints(client):
    client.ok_or_data(f"break-exec ${BOOT_PC}")
    for address in (*PRODOS_RETURNS, PRODOS_ERROR):
        client.ok_or_data(f"break-exec ${address:04X}")


def step_and_rearm(client, address: int):
    client.ok_or_data("break-clear-all")
    client.ok("step-instruction")
    client.ok("wait-paused 3000")
    stepped = client.ok("get-cpu")
    if re.search(rf"\bpc={address:04X}\b", stepped, re.IGNORECASE):
        raise RuntimeError(f"could not step past ${address:04X}: {stepped}")
    arm_boot_breakpoints(client)


def find_game_entry(client, expected_header: bytes, expected_entry: bytes):
    arm_boot_breakpoints(client)
    prodos_calls = []
    address_hits = 0
    for _ in range(MAX_STOPS):
        client.ok("run")
        try:
            client.ok("wait-paused 20000")
        except RuntimeError as error:
            client.ok("pause")
            client.ok("wait-paused 3000")
            raise RuntimeError(
                f"U1.SYSTEM entry not reached after {address_hits} address hits; "
                f"{client.ok('get-cpu')}; {client.ok('get-state')}"
            ) from error
        cpu_reply = client.cmd("get-cpu")
        if cpu_reply[0] != "ok":
            raise RuntimeError(f"get-cpu failed: {cpu_reply}")
        cpu = cpu_reply[1]
        match = re.search(r"\bpc=([0-9A-Fa-f]{4})\b", cpu)
        if not match:
            raise RuntimeError(f"get-cpu lacks PC: {cpu}")
        address = int(match.group(1), 16)
        if address in PRODOS_RETURNS:
            prodos_calls.append(f"{PRODOS_RETURNS[address]}: {cpu}")
            if len(prodos_calls) > 12:
                prodos_calls.pop(0)
            step_and_rearm(client, address)
            continue
        if address == PRODOS_ERROR:
            prodos = (ROOT / "extracted" / "PRODOS").read_bytes()
            if client.mem(address, 6) == prodos[address - 0x2000:address - 0x2000 + 6]:
                raise RuntimeError(
                    "ProDOS relocation/configuration error before U1.SYSTEM; "
                    + "; ".join(prodos_calls[-4:]) + f"; error entry: {cpu}"
                )
            step_and_rearm(client, address)
            continue
        if address != int(BOOT_PC, 16):
            raise RuntimeError(f"unexpected breakpoint: {cpu}")
        address_hits += 1
        if address_hits > MAX_ADDRESS_HITS:
            raise RuntimeError(f"U1.SYSTEM image not found in {MAX_ADDRESS_HITS} hits at ${BOOT_PC}")
        try:
            signature = require_game_image(client, expected_header, expected_entry)
        except RuntimeError as error:
            print(f"skipping earlier ${BOOT_PC} hit {address_hits}: {error}", flush=True)
            step_and_rearm(client, address)
            continue
        return cpu, signature
    raise RuntimeError(f"U1.SYSTEM entry not found after {MAX_STOPS} breakpoint stops")


def sector_image(extractor: Path, disk: Path) -> Path:
    """Make a private block-equivalent floppy for emulators with WOZ read issues."""
    target = OUTPUT / "UltimaI.po"
    record = OUTPUT / "UltimaI.po.json"
    original = describe(disk)
    if target.is_file() and record.is_file():
        saved = json.loads(record.read_text())
        if saved.get("source_sha256") == original["sha256"] and saved.get("image") == describe(target):
            return target
    pending = OUTPUT / f"UltimaI.pending-{os.getpid()}.po"
    pending.unlink(missing_ok=True)
    try:
        subprocess.run([str(extractor), "create-disk-image", str(pending), "140KB", "ProDOS"],
                       check=True, capture_output=True, text=True)
        subprocess.run([str(extractor), "copy-blocks", str(disk), str(pending)],
                       check=True, capture_output=True, text=True)
        if pending.stat().st_size != 143360:
            raise RuntimeError("converted ProDOS floppy has the wrong size")
        pending.replace(target)
        record.write_text(json.dumps({"source_sha256": original["sha256"],
                                      "image": describe(target), "blocks_copied": 280}, indent=2) + "\n")
        return target
    finally:
        pending.unlink(missing_ok=True)


def capture_on_media(client_type, emulator, media, snapshot, log, header, entry):
    snapshot.unlink(missing_ok=True)
    process = launch(emulator, media, None, log)
    try:
        client = connect(client_type, process)
        try:
            client.ok("hello")
            client.ok("wait-paused 3000")  # consume headless startup pause
            cpu, signature = find_game_entry(client, header, entry)
            state = client.ok("get-state")
            client.ok(f"save-state {snapshot}")
            wait_for_snapshot(snapshot)
            return cpu, signature, state
        finally:
            client.s.close()
    finally:
        stop(process)


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
    system = (ROOT / "extracted" / "U1.SYSTEM").read_bytes()
    expected_header, expected_entry = system[:16], system[0x88:0x98]
    sys.path.insert(0, str(source / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    snapshot = OUTPUT / f"boot-2088.pending-{os.getpid()}.a2state"
    snapshot.unlink(missing_ok=True)
    log_path = OUTPUT / "a2m.log"
    with log_path.open("w") as log:
        try:
            cpu, signature, state = capture_on_media(
                Ctl, emulator, disk, snapshot, log, expected_header, expected_entry)
            boot_media = disk
        except RuntimeError as error:
            if not ("ProDOS relocation/configuration error" in str(error)
                    or "U1.SYSTEM entry not reached" in str(error)):
                raise
            print(f"WOZ boot failed: {error}", flush=True)
            extractor_info = manifest.get("extractor")
            if not extractor_info:
                raise RuntimeError("sector-image retry requires a CiderPress extractor") from error
            boot_media = sector_image(Path(extractor_info["path"]), disk)
            print(f"retrying from private block-equivalent image: {boot_media}", flush=True)
            cpu, signature, state = capture_on_media(
                Ctl, emulator, boot_media, snapshot, log, expected_header, expected_entry)

        process = launch(emulator, boot_media, snapshot, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                restored_cpu = wait_for_pc(client)
                require_game_image(client, expected_header, expected_entry)
            finally:
                client.s.close()
        finally:
            stop(process)

    final_snapshot = OUTPUT / "boot-2088.a2state"
    snapshot.replace(final_snapshot)
    snapshot = final_snapshot
    scenario = {
        "name": "cold boot to U1.SYSTEM entry",
        "emulator_revision": revision,
        "model": "Apple //e Enhanced",
        "disk_slot": "s6d0",
        "boot_media": {"path": str(boot_media), **describe(boot_media)},
        "source_disk_sha256": manifest["disk_image"]["sha256"],
        "breakpoint": "0x2088",
        "inputs": [],
        "cpu_at_breakpoint": cpu,
        "state_at_breakpoint": state,
        "cpu_after_snapshot_restore": restored_cpu,
        "verified_memory": signature,
        "snapshot": {"path": str(snapshot), **describe(snapshot)},
    }
    scenario_path = OUTPUT / "boot-2088.json"
    scenario_path.write_text(json.dumps(scenario, indent=2) + "\n")
    runtime["boot_snapshot"] = scenario["snapshot"]
    runtime["boot_media"] = scenario["boot_media"]
    runtime["input_replay"] = {"path": str(scenario_path), "inputs": [],
                               **describe(scenario_path)}
    manifest["runtime"] = runtime
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"captured and restored U1.SYSTEM entry at ${BOOT_PC}")
    print(f"boot media: {boot_media}")
    print(f"private artifacts: {snapshot}, {scenario_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"boot capture failed: {error}", file=sys.stderr)
        raise SystemExit(1)
