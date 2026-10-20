#!/usr/bin/env python3
"""Trace CAS entry through data loads, map copy, and first key poll."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-to-cas" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "cas-first-input"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8956:
        raise RuntimeError("source trace is not at CAS entry")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    tcmaps = (ROOT / "extracted" / "TCMAPS").read_bytes()
    chars = (ROOT / "extracted" / "MAPCHARS").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"first-input.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    maps_match = None
    chars_match = None
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8956:
                    raise RuntimeError("restored CAS entry differs")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "TCMAPS request", (0x898D,)))
                    points.append(wait_at(client, "MAPCHARS request", (0x89A3,)))
                    maps_match = client.mem(0x4000, len(tcmaps)) == tcmaps
                    if not maps_match:
                        raise RuntimeError("TCMAPS load differs from extracted file")
                    points.append(wait_at(client, "castle map copy", (0x89CE,)))
                    chars_match = client.mem(0xB000, len(chars)) == chars
                    if not chars_match:
                        raise RuntimeError("MAPCHARS load differs from extracted file")
                    points.append(wait_at(client, "castle main loop", (0x8A31,)))
                    points.append(wait_at(client, "castle key poll", (0x8A27,)))
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"CAS first-input trace stopped: {timeout}", flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "first-input.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": points, "timeout": timeout,
              "tcmaps_match": maps_match, "mapchars_match": chars_match,
              "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"CAS first-input trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
