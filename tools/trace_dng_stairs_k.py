#!/usr/bin/env python3
"""Replay K at the first observed stair, with chosen direction and depth."""

import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/dng-descend/stairs-turn/poll/handoff.json"
OUTPUT = ROOT / "build/traces/dng-stairs-k"


def dungeon_state(client) -> dict:
    position = client.mem(0xA4E8, 2)
    x, y = position
    return {"position": position.hex(), "facing": client.mem(0xA4EC, 2).hex(),
            "depth": client.mem(0xA506, 1).hex(),
            "tile": client.mem(0xB099 + 11*y + x, 1).hex(),
            "hp": client.mem(0x7EC6, 2).hex(), "food": client.mem(0x7EE5, 2).hex()}


def main(source_report: Path = SOURCE, output: Path = OUTPUT,
         expected_tile: str = "07", expected_depth: str = "01",
         branch: str = "descend") -> int:
    prior = json.loads(source_report.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8DDA:
        raise RuntimeError("source is not at dungeon key poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(source["path"]), Path(disk_item["path"])
    for item, path in ((source, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    pending = output / f"stairs-k.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    timeout = None
    with (output / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8DDA:
                    raise RuntimeError("restored DNG poll differs")
                before = dungeon_state(client)
                if (before["position"] != "0307" or before["facing"] != "0001" or
                        before["tile"] != expected_tile or before["depth"] != expected_depth):
                    raise RuntimeError(f"not at expected stairs: {before}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8DE4")
                client.ok("key 75")
                try:
                    client.ok("wait-paused 15000")
                    cpu = client.ok("get-cpu")
                    if cpu_pc(cpu) != 0x8DE4 or " a=4B " not in cpu:
                        raise RuntimeError(f"K did not return from poll: {cpu}")
                    points.append({"label": "K poll return", "pc": "0x8DE4",
                                   "cpu": cpu, "state": client.ok("get-state")})
                    path = [("command lookup return", 0x8DD7),
                            ("patched call", 0x8E0B),
                            ("K handler", 0x961B),
                            ("stair facing check", 0x963F),
                            ("stair choice", 0x9666)]
                    if branch == "descend":
                        path.append(("descend", 0x972C))
                    elif branch == "ascend":
                        path.extend((("ascend", 0x9670), ("regenerate level", 0x9728)))
                    else:
                        raise ValueError(f"unknown stair branch: {branch}")
                    path.extend((("next-level generator", 0x8C5D),
                                 ("next-level key poll", 0x8DDA)))
                    for label, address in path:
                        points.append(wait_at(client, label, (address,)))
                    if " x=1E " not in points[1]["cpu"]:
                        raise RuntimeError("K did not map to command index 15")
                    if client.mem(0x8E0B, 3) != bytes((0x20, 0x1B, 0x96)):
                        raise RuntimeError("K did not dispatch to $961B")
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"DNG stairs K stopped: {timeout}", flush=True)
                after = dungeon_state(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu, final_state = client.ok("get-cpu"), client.ok("get-state")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = output / "stairs-k.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "input": {"key_ascii": 75, "at_pc": "0x8DDA"},
              "checkpoints": points, "timeout": timeout, "before": before,
              "after": after, "final_cpu": final_cpu, "final_state": final_state,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"DNG stairs K: {before} → {after}")
    print(f"private trace: {path}")
    return 0 if timeout is None else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG stairs K failed: {error}", file=sys.stderr)
        raise SystemExit(1)
