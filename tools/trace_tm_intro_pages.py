#!/usr/bin/env python3
"""Continue TM's Space-gated opening pages from the accepted first page."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tm-page1/probe.json"
OUTPUT = ROOT / "build/traces/tm-intro-pages"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("accepted first-page snapshot differs")
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
                if cpu_pc(client.ok("get-cpu")) != 0x882A:
                    raise RuntimeError("TM first-page accepted PC differs")
                client.ok("set-turbo 8")
                for page in range(2, 5):
                    point = wait_at(client, f"TM page {page} or main loop", (0x87F7, 0x8E5E))
                    points.append(point)
                    if point["pc"] == "0x8E5E":
                        break
                    points.append(wait_at(client, f"TM page {page} key read", (0x881B,)))
                    client.ok_or_data("break-clear-all")
                    client.ok_or_data("break-exec $881E")
                    client.ok("key 32")
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x881E or " a=20 " not in cpu:
                        raise RuntimeError(f"page {page} key differs: {cpu}")
                    points.append({"label": f"TM page {page} key return", "pc": "0x881E", "cpu": cpu})
                    points.append(wait_at(client, f"TM page {page} accepted", (0x882A, 0x881B)))
                    if points[-1]["pc"] != "0x882A":
                        raise RuntimeError(f"page {page} Space not accepted")
                if points[-1]["pc"] != "0x8E5E":
                    points.append(wait_at(client, "TM natural loop", (0x8E5E,)))
                points.append(wait_at(client, "TM first command input", (0x9815,)))
                final = client.ok("get-cpu")
                path = OUTPUT / "first-command-input.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                saved = {"path": str(path), **describe(path)}
            finally:
                client.s.close()
        finally:
            stop(process)
    report = {"source_snapshot_sha256": source["sha256"], "checkpoints": points,
              "final_cpu": final, "snapshot": saved}
    path = OUTPUT / "probe.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private report: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TM intro pages trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
