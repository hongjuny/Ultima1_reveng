#!/usr/bin/env python3
"""Replay a one-letter name and Return through GEN's name-entry screen."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "gen-class-a" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-name-a"


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("name-input snapshot differs from class trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"confirmation.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8E83 or client.mem(0x9042, 1)[0] != 0:
                    raise RuntimeError("snapshot is not at empty name input")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8EC7")
                client.ok("key 65")  # key injection also resumes execution
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8EC7:
                    raise RuntimeError(f"A did not reach name storage: {cpu}")
                print(f"first name character accepted: $8EC7 {cpu}", flush=True)
                points.append({"label": "first character accepted", "pc": "0x8EC7",
                               "cpu": cpu, "state": client.ok("get-state")})
                points.append(wait_at(client, "name input loop", (0x8E83,)))
                if client.mem(0x9042, 1)[0] != 1 or client.mem(0x7EB8, 1)[0] != 65:
                    raise RuntimeError("name A was not stored at $7EB8")
                print("name buffer: length=1 first_character=A", flush=True)
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8EEE")
                client.ok("key 13")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8EEE:
                    raise RuntimeError(f"Return did not reach confirmation: {cpu}")
                if client.mem(0x9042, 1)[0] != 1 or client.mem(0x7EB8, 1)[0] != 65:
                    raise RuntimeError("name changed before confirmation")
                print(f"name confirmation: $8EEE {cpu}", flush=True)
                points.append({"label": "name confirmation", "pc": "0x8EEE",
                               "cpu": cpu, "state": client.ok("get-state")})
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "confirmation.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "input": [{"key_ascii": 65, "at_pc": "0x8E83"},
                        {"key_ascii": 13, "at_pc": "0x8E83"}],
              "checkpoints": points, "name_ascii": [65],
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN name-A trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
