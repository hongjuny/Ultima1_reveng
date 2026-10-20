#!/usr/bin/env python3
"""Replay GEN attribute decrease, lower bound, and selection navigation."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "gen-attribute-increase" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-attribute-controls"
CASES = (
    (0x08, (10, 30, 1), "decrease to minimum"),
    (0x08, (10, 30, 1), "hold at minimum"),
    (0x2F, (10, 30, 2), "select next attribute"),
    (0x0B, (10, 30, 1), "select previous attribute"),
)


def values(client) -> tuple[int, int, int]:
    return (client.mem(0x7EC8, 1)[0], client.mem(0x903F, 1)[0],
            client.mem(0x9041, 1)[0])


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("attribute-increase snapshot differs from trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"controls.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    events = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8C00 or values(client) != (11, 29, 1):
                    raise RuntimeError("snapshot is not at the expected attribute loop state")
                client.ok("set-turbo 8")
                for key, expected, label in CASES:
                    wait_at(client, "GEN attribute key read", (0x8C07,))
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $8C00")
                    client.ok(f"key {key}")  # a2m resumes when the key is injected
                    try:
                        client.ok("wait-paused 15000")
                    except RuntimeError as error:
                        client.ok("pause")
                        client.ok("wait-paused 3000")
                        raise RuntimeError(f"{label}: loop not reached; "
                                           f"{client.ok('get-cpu')}; {client.ok('get-state')}") from error
                    cpu = client.ok("get-cpu")
                    actual = values(client)
                    print(f"{label}: key=${key:02X} state={actual}; {cpu}", flush=True)
                    if cpu_pc(cpu) != 0x8C00 or actual != expected:
                        raise RuntimeError(f"{label}: expected {expected} at $8C00, got {actual}")
                    events.append({"label": label, "key_code": key, "pc": "0x8C00",
                                   "attribute_7EC8": actual[0], "points_903F": actual[1],
                                   "selection_9041": actual[2], "cpu": cpu})
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "after-controls.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "events": events, "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN attribute controls trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
