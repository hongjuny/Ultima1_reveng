#!/usr/bin/env python3
"""Replay GEN menu choice A and capture its new-character branch."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc


SOURCE = ROOT / "build" / "traces" / "gen-menu" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-new-character"
KEY = 65  # ASCII A; GEN compares the normalized value with $41.


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("GEN menu snapshot differs from trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"new-character.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x89FD:
                    raise RuntimeError(f"expected GEN menu key read at $89FD: {cpu}")
                client.ok("set-turbo 8")
                # `key` resumes a2m. Set both possible dispatch targets first.
                client.ok_or_data("break-clear-all")
                for address in (0x8AC3, 0x8A0C):
                    client.ok_or_data(f"break-exec ${address:04X}")
                client.ok(f"key {KEY}")
                try:
                    client.ok("wait-paused 15000")
                except RuntimeError as error:
                    client.ok("pause")
                    client.ok("wait-paused 3000")
                    raise RuntimeError(f"GEN choice did not reach a dispatch target: "
                                       f"{client.ok('get-cpu')}; {client.ok('get-state')}") from error
                cpu = client.ok("get-cpu")
                pc = cpu_pc(cpu)
                print(f"GEN menu choice A: ${pc:04X} {cpu}", flush=True)
                if pc != 0x8AC3:
                    raise RuntimeError(f"choice A did not take new-character branch: {cpu}")
                checkpoint = {"label": "GEN new-character branch", "pc": "0x8AC3",
                              "cpu": cpu, "state": client.ok("get-state")}
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "new-character.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "input": {"key_ascii": KEY, "at_pc": "0x89FD"},
              "checkpoint": checkpoint, "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN new-character trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
