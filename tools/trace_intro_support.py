#!/usr/bin/env python3
"""Trace U1.INTRO's first MAKE.INDATA request from the private handoff snapshot."""

import hashlib
import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build" / "traces" / "intro-support"
HANDOFF = ROOT / "build" / "traces" / "startup" / "handoff.json"


def first_difference(actual: bytes, expected: bytes) -> str | None:
    for index, (left, right) in enumerate(zip(actual, expected)):
        if left != right:
            return f"0x{0x1E00 + index:04X}: memory={left:02X} file={right:02X}"
    if len(actual) != len(expected):
        return f"length {len(actual)} != {len(expected)}"
    return None


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    runtime = manifest["runtime"]
    handoff = json.loads(HANDOFF.read_text())
    source = handoff["snapshot"]
    source_path = Path(source["path"])
    if describe(source_path) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("intro-entry snapshot differs from handoff trace")
    media = runtime.get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk)["sha256"] != media["sha256"]:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(runtime["emulator"]["path"])
    intro = (ROOT / "extracted" / "U1.INTRO").read_bytes()
    support = (ROOT / "extracted" / "MAKE.INDATA").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"support-loaded.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source_path}")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x0F23:
                    raise RuntimeError(f"expected U1.INTRO $0F23 after restore: {cpu}")
                if client.mem(0x0800, 16) != intro[:16] or client.mem(0x0F23, 16) != intro[0x723:0x733]:
                    raise RuntimeError("restored U1.INTRO code differs from extraction")
                entry = wait_at(client, "MAKE.INDATA loader entry", (0xB70C,))
                entry["loader_code_hex"] = client.mem(0xB70C, 16).hex()
                checkpoints.append(entry)
                result = wait_at(client, "MAKE.INDATA loader return", (0x0F37,))
                checkpoints.append(result)
                status = int(result["cpu"].split(" p=")[1][:2], 16)
                result["carry_set"] = bool(status & 1)
                loaded = client.mem(0x1E00, len(support))
                result["loaded_sha256"] = hashlib.sha256(loaded).hexdigest()
                result["file_sha256"] = hashlib.sha256(support).hexdigest()
                result["first_difference"] = first_difference(loaded, support)
                print(f"MAKE.INDATA memory match: {result['first_difference'] is None}", flush=True)
                if result["carry_set"]:
                    raise RuntimeError(f"MAKE.INDATA loader returned carry set: {result['cpu']}")
                next_point = wait_at(client, "intro after support request", (0x0F28, 0x0F41))
                checkpoints.append(next_point)
                if next_point["pc"] == "0x0F28":
                    raise RuntimeError("U1.INTRO retried the MAKE.INDATA request")
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "support-loaded.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "checkpoints": checkpoints,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"intro support trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
