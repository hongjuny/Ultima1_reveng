#!/usr/bin/env python3
"""Reload the outdoor Q save from GEN's previous-character menu."""

import hashlib
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_startup import cpu_pc, wait_at
from verify_intro_support import main_ram


MENU = ROOT / "build/traces/gen-after-save/handoff.json"
SAVE = ROOT / "build/traces/out-player-save/handoff.json"
OUTPUT = ROOT / "build/traces/out-player-reload"
START = 0x7E6D
LENGTH = 0x01CA


def main():
    menu = json.loads(MENU.read_text())
    saved = json.loads(SAVE.read_text())
    source = menu["snapshot"]
    player_disk = saved["working_player_disk"]
    for item in (source, player_disk, saved["snapshot"]):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    expected = main_ram(Path(saved["snapshot"]["path"]))[START:START+LENGTH]
    original = main_ram(Path(source["path"]))[START:START+LENGTH]
    if expected == original:
        raise RuntimeError("outdoor save has no changed record bytes")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "loaded.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(player_disk["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x89FD:
                    raise RuntimeError("restored GEN menu differs")
                if client.mem(START, LENGTH) != original:
                    raise RuntimeError("GEN source record differs")
                client.ok("unmount kind=diskii 6 0")
                client.ok(f"mount-disk 6 0 {player_disk['path']}")
                client.ok("set-turbo 8")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8A10")
                client.ok("key 66")
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8A10:
                    raise RuntimeError("B did not reach GEN load")
                points = [{"pc": "0x8A10", "cpu": client.ok("get-cpu")}]
                points.append(wait_at(client, "Q-save load return", (0x8A1C,)))
                if (status_carry(points[-1]["cpu"]) or
                        client.mem(0x6000, LENGTH) != expected):
                    raise RuntimeError("GEN load did not recover outdoor Q save")
                points.append(wait_at(client, "Q-save record copy", (0x8A7F,)))
                if client.mem(START, LENGTH) != expected:
                    raise RuntimeError("GEN live record differs from Q save")
                points.append(wait_at(client, "Q-save OUT handoff", (0x8AC0,)))
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    report = {"source_snapshot": source, "save_snapshot": saved["snapshot"],
              "player_disk": player_disk, "input": 66,
              "checkpoints": points,
              "original_record_sha256": hashlib.sha256(original).hexdigest(),
              "loaded_record_sha256": hashlib.sha256(expected).hexdigest(),
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print("GEN B: outdoor Q save loaded at $6000, copied to $7E6D, handed to OUT")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"OUT player-reload trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
