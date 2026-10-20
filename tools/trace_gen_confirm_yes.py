#!/usr/bin/env python3
"""Replay GEN's save confirmation using a private copy of the boot disk."""

import json
import os
from pathlib import Path
import shutil
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "gen-name-a" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-confirm-yes"


def status_carry(cpu: str) -> bool:
    for token in cpu.split():
        if token.startswith("p="):
            return bool(int(token[2:], 16) & 1)
    raise RuntimeError(f"CPU status missing: {cpu}")


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("confirmation snapshot differs from name trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    original_disk = Path(media["path"])
    if describe(original_disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    # a2m snapshots contain the mounted image's absolute path. Keep its byte
    # length so the snapshot can be redirected without changing its structure.
    working_disk = original_disk.with_name("UltimaR.po")
    if len(os.fsencode(working_disk)) != len(os.fsencode(original_disk)):
        raise RuntimeError("working disk path must have the original path length")
    shutil.copyfile(original_disk, working_disk)
    raw = snapshot.read_bytes()
    old_path = os.fsencode(original_disk)
    if raw.count(old_path) != 1:
        raise RuntimeError("snapshot does not contain exactly one original disk path")
    patched = OUTPUT / "confirmation-working.a2state"
    patched.write_bytes(raw.replace(old_path, os.fsencode(working_disk)))
    pending = OUTPUT / f"after-save.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, working_disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {patched}")
                if cpu_pc(client.ok("get-cpu")) != 0x8EEE:
                    raise RuntimeError("snapshot is not at name confirmation")
                if client.mem(0x9042, 1)[0] != 1 or client.mem(0x7EB8, 1)[0] != 65:
                    raise RuntimeError("name A is missing after snapshot restore")
                client.ok("set-turbo 8")
                points.append(wait_at(client, "confirmation key read", (0x8F12,)))
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8F23")
                client.ok("key 89")  # Y; injection resumes execution
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8F23:
                    raise RuntimeError(f"Y did not reach save call: {cpu}")
                print(f"confirmation Y: $8F23 {cpu}", flush=True)
                points.append({"label": "confirmation Y", "pc": "0x8F23",
                               "cpu": cpu, "state": client.ok("get-state")})
                points.append(wait_at(client, "save call return", (0x8F2C,)))
                carry = status_carry(points[-1]["cpu"])
                print(f"save call carry set: {carry}", flush=True)
                points.append(wait_at(client, "post-save branch", (0x895B, 0x8F31)))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    if describe(original_disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("original boot media changed during save replay")
    final = OUTPUT / "after-save.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "working_snapshot": {"path": str(patched), **describe(patched)},
              "working_disk": {"path": str(working_disk), **describe(working_disk)},
              "input": {"key_ascii": 89, "at_pc": "0x8F12"},
              "checkpoints": points, "save_carry_set": carry,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN confirmation-Y trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
