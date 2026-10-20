#!/usr/bin/env python3
"""Trace GEN from its entry to the first character-menu key read."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "engine-to-gen" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-menu"


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("GEN entry snapshot differs from trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"menu-key.pending-{os.getpid()}.a2state"
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
                if cpu_pc(cpu) != 0x8956:
                    raise RuntimeError(f"expected GEN entry at $8956: {cpu}")
                gen = (ROOT / "extracted" / "GEN").read_bytes()
                if client.mem(0x8956, 16) != gen[:16]:
                    raise RuntimeError("GEN entry bytes differ from extraction")
                client.ok("set-turbo 8")
                menu = wait_at(client, "GEN menu key read", (0x89FD,))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "menu-key.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "checkpoint": menu, "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN menu trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
