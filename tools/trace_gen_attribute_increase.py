#!/usr/bin/env python3
"""Replay GEN's $15 increase key for the first character attribute."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc


SOURCE = ROOT / "build" / "traces" / "gen-first-input" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-attribute-increase"
KEY = 0x15


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("first-input snapshot differs from trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"after-increase.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8C07:
                    raise RuntimeError("snapshot is not at GEN's first attribute input")
                before = {"attribute_7EC8": client.mem(0x7EC8, 1)[0],
                          "points_903F": client.mem(0x903F, 1)[0],
                          "selection_9041": client.mem(0x9041, 1)[0]}
                if before != {"attribute_7EC8": 10, "points_903F": 30,
                              "selection_9041": 1}:
                    raise RuntimeError(f"unexpected initial attribute state: {before}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8C00")
                client.ok(f"key {KEY}")  # `key` resumes the paused runtime.
                try:
                    client.ok("wait-paused 15000")
                except RuntimeError as error:
                    client.ok("pause")
                    client.ok("wait-paused 3000")
                    raise RuntimeError(f"attribute loop not reached: "
                                       f"{client.ok('get-cpu')}; {client.ok('get-state')}") from error
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8C00:
                    raise RuntimeError(f"unexpected stop after increase key: {cpu}")
                after = {"attribute_7EC8": client.mem(0x7EC8, 1)[0],
                         "points_903F": client.mem(0x903F, 1)[0],
                         "selection_9041": client.mem(0x9041, 1)[0]}
                print(f"GEN attribute increase: {before} → {after}; {cpu}", flush=True)
                if after != {"attribute_7EC8": 11, "points_903F": 29,
                             "selection_9041": 1}:
                    raise RuntimeError(f"attribute increase differs from reviewed code: {after}")
                checkpoint = {"label": "GEN attribute loop after increase",
                              "pc": "0x8C00", "cpu": cpu, "state": client.ok("get-state")}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "after-increase.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "input": {"key_code": KEY, "at_pc": "0x8C07"},
              "before": before, "after": after, "checkpoint": checkpoint,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN attribute increase trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
