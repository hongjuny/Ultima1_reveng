#!/usr/bin/env python3
"""Force only a pending OUT move to the east world boundary."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/out-world-boundary"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def state(client):
    return {f"${address:04X}": client.mem(address, 1)[0]
            for address in (0x0000, 0x0001, 0x000C, 0x000D,
                            0x7E6F, 0x7E70, 0x7EF6)}


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("OUT source is not at first input")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = checked(source), checked(disk_item)
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
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("restored OUT PC differs")
                initial = state(client)
                map_initial = hashlib.sha256(client.mem(0x6000, 4096)).hexdigest()
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A74")
                client.ok("key 11")
                client.ok("wait-paused 15000")
                cpu = client.ok("get-cpu")
                if cpu_pc(cpu) != 0x8A74 or " a=0B " not in cpu:
                    raise RuntimeError(f"Up key did not return: {cpu}")
                points.append({"label": "Up returned", "pc": "0x8A74", "cpu": cpu})
                points.append(wait_at(client, "OUT move commit", (0x9416,)))
                before = state(client)
                if before["$7E6F"] != 0:
                    raise RuntimeError("source is not in world segment zero")
                client.set_mem(0x000C, b"\x4A")
                intervened = state(client)
                points.append(wait_at(client, "boundary test", (0x9477,)))
                points.append(wait_at(client, "east boundary", (0x9496,)))
                points.append(wait_at(client, "world index mask", (0x94C1,)))
                masked = state(client)
                points.append(wait_at(client, "world bits encode", (0x9503,)))
                encoded_before = state(client)
                points.append(wait_at(client, "world map ready", (0x952C,)))
                encoded = state(client)
                map_after = hashlib.sha256(client.mem(0x6000, 4096)).hexdigest()
                points.append(wait_at(client, "OUT next input", (0x8A6C,)))
                final = state(client)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "key": 11, "points": points, "initial": initial,
              "before_intervention": before, "intervened": intervened,
              "masked": masked, "encoded_before": encoded_before,
              "encoded": encoded, "final": final,
              "map_initial_sha256": map_initial,
              "map_after_sha256": map_after,
              "final_cpu": final_cpu}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"world {before['$7E6F']} → {final['$7E6F']}, "
          f"world bits ${final['$7E70']:02X}, "
          f"X ${final['$0000']:02X}; map changed {map_initial != map_after}")
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"OUT world-boundary trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
