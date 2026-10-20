#!/usr/bin/env python3
"""Replay GEN menu B to reload the saved U1.VARS character."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_startup import cpu_pc, wait_at
from verify_intro_support import main_ram


SOURCE = ROOT / "build" / "traces" / "gen-after-save" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-load-player"
RECORD_LENGTH = 0x01CA


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("GEN menu snapshot differs from after-save trace")
    disk_item = prior["player_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("player disk differs from after-save trace")
    expected_record = main_ram(snapshot)[0x7E6D:0x7E6D + RECORD_LENGTH]
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"out-handoff.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x89FD:
                    raise RuntimeError("snapshot is not at GEN A/B input")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A10")
                client.ok("key 66")  # B: previous character
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A10:
                    raise RuntimeError("B did not reach player load")
                print(f"menu B: $8A10 {client.ok('get-cpu')}", flush=True)
                points.append({"label": "menu B", "pc": "0x8A10",
                               "cpu": client.ok("get-cpu"), "state": client.ok("get-state")})
                points.append(wait_at(client, "player load return", (0x8A1C,)))
                if status_carry(points[-1]["cpu"]):
                    raise RuntimeError("U1.VARS load returned with carry set")
                if client.mem(0x6000, RECORD_LENGTH) != expected_record:
                    raise RuntimeError("loaded U1.VARS differs from saved record")
                print("loaded U1.VARS: 458 bytes match saved record at $6000", flush=True)
                points.append(wait_at(client, "record header accepted", (0x8A5B,)))
                points.append(wait_at(client, "record copy complete", (0x8A7F,)))
                if client.mem(0x7E6D, RECORD_LENGTH) != expected_record:
                    raise RuntimeError("reloaded record differs at $7E6D")
                print("record copy: $6000-$61C9 → $7E6D-$8036 matched", flush=True)
                points.append(wait_at(client, "OUT handoff jump", (0x8AC0,)))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("player disk changed during reload")
    final = OUTPUT / "out-handoff.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "player_disk": disk_item,
              "input": {"key_ascii": 66, "at_pc": "0x89FD"},
              "checkpoints": points, "record_length": RECORD_LENGTH,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN player-load trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
