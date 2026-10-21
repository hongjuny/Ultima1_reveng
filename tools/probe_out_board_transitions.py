#!/usr/bin/env python3
"""Exercise OUT's B command and controlled SPA/TM transition gates."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/out-board-transitions"


def trial(client, snapshot, mode):
    client.ok(f"load-state {snapshot}")
    if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
        raise RuntimeError("OUT poll snapshot differs")
    x, y = client.mem(0, 2)
    map_address = 0x6000 + 64 * y + x
    initial = {"position": [x, y], "craft_7E7C": client.mem(0x7E7C, 1)[0],
               "map_address": f"${map_address:04X}",
               "map_raw": client.mem(map_address, 1)[0]}
    if mode != "ordinary":
        client.set_mem(0x7E7C, b"\x00")  # $00 means not already aboard
        client.set_mem(map_address, b"\x1c" if mode == "spa" else b"\x1e")
        if mode == "tm":
            client.set_mem(0x7E75, b"\x01\x01\x01\x01")
    client.ok("set-turbo 8")
    client.ok_or_data("break-clear-all")
    client.ok_or_data("break-exec $8A74")
    client.ok("key 66")  # B
    client.ok("wait-paused 15000")
    if cpu_pc(client.ok("get-cpu")) != 0x8A74:
        raise RuntimeError("B did not return from poll")
    points = []
    points.append(wait_at(client, "B handler", (0x8CF0,)))
    points.append(wait_at(client, "craft check result", (0x8D14, 0x89DF)))
    if points[-1]["pc"] == "0x8D14":
        points.append(wait_at(client, "tile gate", (0x8D1F, 0x8D42)))
    if mode != "ordinary":
        if points[-1]["pc"] != "0x8D42":
            raise RuntimeError("controlled craft did not pass tile gate")
        branch = 0x8D6E if mode == "spa" else 0x8D73
        points.append(wait_at(client, "module branch", (0x8D6E, 0x8D73)))
        if points[-1]["pc"] != f"0x{branch:04X}":
            raise RuntimeError("controlled tile selected a different module")
        points.append(wait_at(client, "common selector", (0x88FD,)))
        overlay, selector = ("SPA", 0x14) if mode == "spa" else ("TM", 0x18)
        if f" a={selector:02X} " not in points[-1]["cpu"]:
            raise RuntimeError("module selector value differs")
        points.append(wait_at(client, f"{overlay} entry", (0x8956,)))
        expected = (ROOT / "extracted" / overlay).read_bytes()
        if client.mem(0x8956, len(expected)) != expected:
            raise RuntimeError(f"{overlay} overlay bytes differ")
        points.append(wait_at(client, f"{overlay} entry target",
                              (0x8A53 if mode == "spa" else 0x8AD7,)))
        if mode == "spa":
            points.append(wait_at(client, "SPA first command input", (0x8A5F,)))
        if mode == "tm":
            points.append(wait_at(client, "TM first page prompt", (0x87F7,)))
            points.append(wait_at(client, "TM first page key read", (0x881B,)))
    page_snapshot = None
    if mode in ("spa", "tm"):
        path = OUTPUT / ("spa-first-input.a2state" if mode == "spa"
                         else "tm-first-page-key.a2state")
        path.unlink(missing_ok=True)
        client.ok(f"save-state {path}")
        wait_for_snapshot(path)
        time.sleep(0.2)  # a2m can append the final 16-byte trailer after the file appears
        page_snapshot = {"path": str(path), **describe(path)}
    return {"mode": mode, "initial": initial,
            "craft_after": client.mem(0x7E7C, 1)[0], "checkpoints": points,
            "final_cpu": client.ok("get-cpu"), "snapshot": page_snapshot}


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source does not stop at OUT poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {}
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                for name in ("ordinary", "spa", "tm"):
                    result[name] = trial(client, snapshot, name)
            finally:
                client.s.close()
        finally:
            stop(process)
    path = OUTPUT / "probe.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"private report: {path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT boarding probe failed: {error}", file=sys.stderr)
        raise SystemExit(1)
