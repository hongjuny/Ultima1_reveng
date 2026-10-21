#!/usr/bin/env python3
"""Inspect the first TM intro prompt after the controlled B transition."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-board-transitions/probe.json"
OUTPUT = ROOT / "build/traces/tm-page1"


def main():
    prior = json.loads(SOURCE.read_text())["tm"]
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("TM prompt snapshot differs")
    disk_item = json.loads((ROOT / "build/traces/out-first-input/handoff.json").read_text())["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working disk differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x881B:
                    raise RuntimeError("TM prompt PC differs")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $881E")
                client.ok("key 32")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x881E:
                    raise RuntimeError(f"TM key return did not reach $881E: {cpu}")
                points.append({"label": "TM key return", "pc": "0x881E", "cpu": cpu})
                points.append(wait_at(client, "TM prompt accepted or repeat", (0x882A, 0x881B)))
                if points[-1]["pc"] != "0x882A":
                    raise RuntimeError("TM Space was not accepted")
                accepted_path = OUTPUT / "accepted.a2state"
                accepted_path.unlink(missing_ok=True)
                client.ok(f"save-state {accepted_path}")
                wait_for_snapshot(accepted_path)
                time.sleep(0.2)
                accepted = {"path": str(accepted_path), **describe(accepted_path)}
                final = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    result = {"source_snapshot_sha256": source["sha256"], "key": 32,
              "checkpoints": points, "final_cpu": final, "snapshot": accepted}
    path = OUTPUT / "probe.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"private report: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TM page 1 trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
