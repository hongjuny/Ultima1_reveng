#!/usr/bin/env python3
"""Report the naturally completed odd quest to the second castle king."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/odd-quest-return-king-route/step-28/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-natural-gem-award"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source is not at castle input")
    snapshot, disk = checked(prior["snapshot"]), checked(prior["working_game_disk"])
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A27:
                    raise RuntimeError("restored castle input differs")
                initial = {"position": list(client.mem(0, 2)),
                           "index": client.mem(0x9E3B, 1)[0],
                           "king_tile": client.mem(0xB400 + 6*38 + 25, 1)[0],
                           "quest": list(client.mem(0x7EA9, 8)),
                           "gems": list(client.mem(0x7E75, 4)),
                           "group": client.mem(0x7E6F, 1)[0]}
                if initial != {"position": [25, 6], "index": 1,
                               "king_tile": 0x6C,
                               "quest": [0, 255, 0, 0, 0, 0, 0, 0],
                               "gems": [0] * 4, "group": 0}:
                    raise RuntimeError(f"source state differs: {initial}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok("key 84")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A2F:
                    raise RuntimeError("T did not return from castle poll")
                points = [wait_at(client, "king tile", (0x92AA,)),
                          wait_at(client, "completed quest", (0x92CC,)),
                          wait_at(client, "reward entry", (0x94E7,)),
                          wait_at(client, "odd quest reward", (0x959D,)),
                          wait_at(client, "gem selector", (0x95BC,)),
                          wait_at(client, "red gem write", (0x963A,)),
                          wait_at(client, "gem write complete", (0x963D,))]
                final = {"quest": list(client.mem(0x7EA9, 8)),
                         "gems": list(client.mem(0x7E75, 4)),
                         "index": client.mem(0x9E3B, 1)[0]}
                path = OUTPUT / "award.a2state"
                path.unlink(missing_ok=True)
                client.ok(f"save-state {path}")
                wait_for_snapshot(path)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "initial": initial, "input": 84,
                          "checkpoints": points, "final": final,
                          "snapshot": {"path": str(path), **describe(path)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"natural red gem award: {initial} → {final}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"natural castle gem trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
