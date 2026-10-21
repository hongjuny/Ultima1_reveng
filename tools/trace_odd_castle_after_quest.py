#!/usr/bin/env python3
"""Continue the accepted king quest to the next castle key poll."""

import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/odd-castle-quest-accept/handoff.json"
OUTPUT = ROOT / "build/traces/odd-castle-after-quest"


def main():
    prior = json.loads(SOURCE.read_text())
    snapshot_item, disk_item = prior["snapshot"], prior["working_game_disk"]
    snapshot, disk = Path(snapshot_item["path"]), Path(disk_item["path"])
    for item, path in ((snapshot_item, snapshot), (disk_item, disk)):
        if describe(path) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {path}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "next-poll.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x943A:
                    raise RuntimeError("restored quest checkpoint differs")
                client.ok("set-turbo 8")
                message = wait_at(client, "quest message key wait", (0x160D,))
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A27")
                client.ok("key 32")  # Continue the king's text with Space.
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A27:
                    raise RuntimeError("quest message did not return to castle poll")
                point = {"label": "next castle poll", "pc": "0x8A27",
                         "cpu": client.ok("get-cpu"), "state": client.ok("get-state")}
                quest = list(client.mem(0x7EA9, 8))
                position = list(client.mem(0, 2))
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": snapshot_item,
                          "working_game_disk": disk_item,
                          "input": {"key_ascii": 32, "at_pc": "0x160D"},
                          "checkpoints": [message, point], "timeout": None,
                          "quest": quest, "position": position,
                          "final_cpu": client.ok("get-cpu"),
                          "final_state": client.ok("get-state"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    if quest != [0, 1, 0, 0, 0, 0, 0, 0] or position != [25, 6]:
        raise RuntimeError(f"accepted state changed after turn: {quest}, {position}")
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"next castle poll: position={position} quest={quest}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"castle quest continuation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
