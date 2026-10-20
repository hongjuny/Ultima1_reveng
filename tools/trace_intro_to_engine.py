#!/usr/bin/env python3
"""Replay one intro key and trace the MI.U1 engine load."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


OUTPUT = ROOT / "build" / "traces" / "intro-to-engine"
SUPPORT_TRACE = ROOT / "build" / "traces" / "intro-support" / "handoff.json"
KEY = 65  # ASCII 'A'; Apple keyboard presents it with the high bit set.


def wait_for_animation_key_poll(client):
    """Allow the initial screen construction to finish before the first poll."""
    client.ok_or_data("break-clear-all")
    client.ok_or_data("break-exec $0B23")
    client.ok("run")
    for attempt in range(3):
        try:
            client.ok("wait-paused 15000")
            cpu = client.ok("get-cpu")
            if cpu_pc(cpu) != 0x0B23:
                raise RuntimeError(f"unexpected stop during intro drawing: {cpu}")
            state = client.ok("get-state")
            print(f"intro animation key poll: $0B23 {cpu}", flush=True)
            return {"label": "intro animation key poll", "pc": "0x0B23",
                    "cpu": cpu, "state": state}
        except RuntimeError as error:
            if "timeout" not in str(error):
                raise
            print(f"waiting for first animation key poll ({attempt + 1}/3): "
                  f"{client.ok('get-cpu')}", flush=True)
    client.ok("pause")
    client.ok("wait-paused 3000")
    raise RuntimeError(f"animation key poll not reached: {client.ok('get-cpu')}; "
                       f"{client.ok('get-state')}")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    runtime = manifest["runtime"]
    support_trace = json.loads(SUPPORT_TRACE.read_text())
    source = support_trace["snapshot"]
    source_path = Path(source["path"])
    if describe(source_path) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("support-loaded snapshot differs from trace")
    media = runtime.get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk)["sha256"] != media["sha256"]:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(runtime["emulator"]["path"])
    engine = (ROOT / "extracted" / "MI.U1").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    prekey = OUTPUT / f"intro-key-ready.pending-{os.getpid()}.a2state"
    pending = OUTPUT / f"engine-entry.pending-{os.getpid()}.a2state"
    prekey.unlink(missing_ok=True)
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
                if cpu_pc(cpu) != 0x0F41:
                    raise RuntimeError(f"expected intro $0F41 after restore: {cpu}")
                client.ok("set-turbo 8")
                ready = wait_for_animation_key_poll(client)
                checkpoints.append(ready)
                client.ok(f"save-state {prekey}")
                wait_for_snapshot(prekey)
                client.ok(f"key {KEY}")
                key_path = wait_at(client, "intro key dispatch", (0x0B50,))
                checkpoints.append(key_path)
                if "a=C1" not in key_path["cpu"]:
                    raise RuntimeError(f"unexpected intro key code: {key_path['cpu']}")
                checkpoints.append(wait_at(client, "MI.U1 loader entry", (0xB70C,)))
                entry = wait_at(client, "MI.U1 entry", (0x7000, 0x8956))
                checkpoints.append(entry)
                if client.mem(0x7000, 16) != engine[:16]:
                    raise RuntimeError("MI.U1 entry bytes differ from extraction")
                loaded = client.mem(0x7000, len(engine))
                entry["file_bytes_match_at_entry"] = loaded == engine
                if not entry["file_bytes_match_at_entry"]:
                    entry["first_difference"] = next(
                        f"0x{0x7000 + i:04X}" for i, (a, b) in enumerate(zip(loaded, engine)) if a != b
                    )
                if entry["pc"] == "0x7000":
                    checkpoints.append(wait_at(client, "MI.U1 first loader", (0x8956,)))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final_prekey = OUTPUT / "intro-key-ready.a2state"
    final_engine = OUTPUT / "engine-entry.a2state"
    prekey.replace(final_prekey)
    pending.replace(final_engine)
    report = {"source_snapshot": source, "boot_media": media,
              "inputs": [{"key_ascii": KEY, "at_checkpoint": "intro animation key poll",
                          "state_before_input": checkpoints[0]["state"]}],
              "checkpoints": checkpoints,
              "prekey_snapshot": {"path": str(final_prekey), **describe(final_prekey)},
              "engine_snapshot": {"path": str(final_engine), **describe(final_engine)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, StopIteration) as error:
        print(f"intro-to-engine trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
