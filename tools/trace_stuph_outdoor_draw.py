#!/usr/bin/env python3
"""Measure the resident outdoor draw call from the first OUT input poll."""

import hashlib
import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/stuph-outdoor-draw"
RANGES = (("zero_page", 0x0000, 0x0100),
          ("tile_patterns", 0x0C00, 0x0200),
          ("row_tables", 0x1200, 0x0200),
          ("support_state", 0x1750, 0x0040),
          ("video", 0x2000, 0x4000),
          ("world_map", 0x6000, 0x1000))


def capture(client):
    return {name: client.mem(start, length, "main")
            for name, start, length in RANGES}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def summarize(before, after):
    result = {}
    for name, start, _ in RANGES:
        a, b = before[name], after[name]
        changes = [{"address": f"${start+i:04X}", "before": f"${old:02X}",
                    "after": f"${new:02X}"}
                   for i, (old, new) in enumerate(zip(a, b)) if old != new]
        result[name] = {"before_sha256": digest(a), "after_sha256": digest(b),
                        "changed_count": len(changes),
                        "first_changes": changes[:48]}
    return result


def main():
    prior = json.loads(SOURCE.read_text())
    if cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source snapshot is not at first OUT poll")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("source snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"draw.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("snapshot did not restore at OUT poll")
                original = (ROOT / "extracted/STUPH").read_bytes()
                resident = client.mem(0x1C39, 0x12B)
                mutable = {0x1CEB, 0x1CEC, 0x1CEE, 0x1CEF}
                if any(actual != expected for i, (actual, expected) in
                       enumerate(zip(resident, original[0x1439:0x1564]))
                       if 0x1C39 + i not in mutable):
                    raise RuntimeError("resident outdoor draw differs from extracted STUPH")
                client.ok("set-turbo 8")
                entry = wait_at(client, "outdoor draw entry", (0x1C39,))
                before = capture(client)
                frame_before = client.get_frame()
                returned = wait_at(client, "outdoor draw return", (0x1DA6,))
                after = capture(client)
                frame_after = client.get_frame()
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "draw.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "entry": entry, "return": returned, "final_cpu": final_cpu,
              "memory": summarize(before, after),
              "frame_before": {"number": frame_before["frame"],
                               "sha256": digest(frame_before["pixels"])},
              "frame_after": {"number": frame_after["frame"],
                              "sha256": digest(frame_after["pixels"])},
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("draw call:", entry["cpu"], "→", returned["cpu"])
    print("memory changes:", {name: item["changed_count"]
                              for name, item in report["memory"].items()})
    print("private trace:", path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"STUPH outdoor draw trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
