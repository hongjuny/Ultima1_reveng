#!/usr/bin/env python3
"""Accept the second castle king's quest with ordinary T and S inputs."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/odd-castle-king-route/step-28/handoff.json"
OUTPUT = ROOT / "build/traces/odd-castle-quest-accept"


def checked(item):
    path = Path(item["path"])
    if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
        raise RuntimeError(f"private input changed: {path}")
    return path


def main():
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x8A27:
        raise RuntimeError("source does not stop at the castle poll")
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
                before = {"position": list(client.mem(0, 2)),
                          "quest": list(client.mem(0x7EA9, 8)),
                          "world_location": client.mem(0x7EED, 1)[0],
                          "group": client.mem(0x7E6F, 1)[0],
                          "castle_index": client.mem(0x9E3B, 1)[0],
                          "king_tile": client.mem(0xB400 + 6 * 38 + 25, 1)[0]}
                if before != {"position": [25, 6], "quest": [0] * 8,
                              "world_location": 1, "group": 0,
                              "castle_index": 1, "king_tile": 0x6C}:
                    raise RuntimeError(f"king approach state differs: {before}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A2F")
                client.ok("key 84")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A2F:
                    raise RuntimeError("T did not return from castle poll")
                points = [wait_at(client, "talk handler", (0x927C,)),
                          wait_at(client, "king tile accepted", (0x92AA,)),
                          wait_at(client, "quest status", (0x92CC,)),
                          wait_at(client, "king prompt input", (0x8A25,))]
                if client.mem(0x7EAA, 1) != b"\x00":
                    raise RuntimeError("quest changed before acceptance")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $9301")
                client.ok("key 83")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x9301:
                    raise RuntimeError("S did not return from king prompt")
                points.append(wait_at(client, "service choice", (0x93FB,)))
                points.append(wait_at(client, "quest accepted", (0x9437,)))
                points.append(wait_at(client, "quest increment complete", (0x943A,)))
                after = list(client.mem(0x7EA9, 8))
                final = OUTPUT / "accepted.a2state"
                final.unlink(missing_ok=True)
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": prior["snapshot"],
                          "working_game_disk": prior["working_game_disk"],
                          "before": before, "after_quest": after,
                          "inputs": [84, 83], "checkpoints": points,
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    output = OUTPUT / "handoff.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"second castle quest: {before['quest']} → {after}")
    print(f"private trace: {output}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd castle quest acceptance failed: {error}", file=sys.stderr)
        raise SystemExit(1)
