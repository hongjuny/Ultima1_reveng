#!/usr/bin/env python3
"""Replay GEN sex choice A and reach its class selection menu."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "gen-race-a" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-sex-a"
KEY = 65


def main() -> int:
    source = json.loads(SOURCE.read_text())["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("sex-menu snapshot differs from race trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    disk = Path(media["path"])
    if describe(disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"class-menu.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x8D72:
                    raise RuntimeError("snapshot is not at the sex choice input")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8D83")
                client.ok(f"key {KEY}")  # a2m resumes when key is injected
                try:
                    client.ok("wait-paused 15000")
                except RuntimeError as error:
                    client.ok("pause")
                    client.ok("wait-paused 3000")
                    raise RuntimeError(f"sex choice not accepted: "
                                       f"{client.ok('get-cpu')}; {client.ok('get-state')}") from error
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8D83 or client.mem(0x7EB7, 1)[0] != 0:
                    raise RuntimeError(f"sex A did not store zero at $7EB7: {cpu}")
                print(f"sex A selected: $8D83 $7EB7=00 {cpu}", flush=True)
                points.append({"label": "sex A selected", "pc": "0x8D83",
                               "cpu": cpu, "state": client.ok("get-state")})
                points.append(wait_at(client, "class choice input", (0x8DEA,)))
                if client.mem(0x7EB7, 1)[0] != 0:
                    raise RuntimeError("sex ID changed before class input")
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "class-menu.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "input": {"key_ascii": KEY, "at_pc": "0x8D72"},
              "checkpoints": points, "sex_id_7EB7": 0,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN sex-A trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
