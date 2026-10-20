#!/usr/bin/env python3
"""Retry GEN save after mounting a disposable U1.PLAYER disk."""

import json
import os
from pathlib import Path
import shutil
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "gen-confirm-yes" / "handoff.json"
PLAYER = ROOT / "build" / "baseline" / "U1PLAYER.po"
OUTPUT = ROOT / "build" / "traces" / "gen-player-save"


def main() -> int:
    previous = json.loads(SOURCE.read_text())
    source = previous["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("save-error snapshot differs from prior trace")
    if [p["pc"] for p in previous["checkpoints"][-2:]] != ["0x8F2C", "0x8F31"]:
        raise RuntimeError("prior trace is not at the save-error branch")
    if not PLAYER.is_file():
        raise RuntimeError("player disk missing; run tools/create_player_disk.py")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    original_disk = Path(media["path"])
    if describe(original_disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("boot media differs from baseline")
    # The error snapshot mounts UltimaR.po. It remains a private, unchanged copy
    # of the original game disk and is replaced with a player disk before retry.
    working_game = Path(previous["working_disk"]["path"])
    if describe(working_game) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("working game disk changed after failed save")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Use a new disposable player disk copy; preserve the blank template.
    working_player = OUTPUT / "player-working.po"
    shutil.copyfile(PLAYER, working_player)
    blank_player = describe(working_player)
    pending = OUTPUT / f"saved.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, working_game, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8F31:
                    raise RuntimeError("snapshot is not at save-error branch")
                client.ok("set-turbo 8")
                points.append(wait_at(client, "player disk prompt", (0x8F9A,)))
                client.ok("unmount 6 0")
                client.ok(f"mount-disk 6 0 {working_player}")
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8EEE")
                client.ok("key 78")  # N: decline in-game formatting, retry save
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8EEE:
                    raise RuntimeError("N did not return to save confirmation")
                print("player disk mounted; returned to confirmation", flush=True)
                points.append({"label": "retry confirmation", "pc": "0x8EEE",
                               "cpu": client.ok("get-cpu"), "state": client.ok("get-state")})
                points.append(wait_at(client, "confirmation key read", (0x8F12,)))
                client.ok_or_data("break-clear-all")
                client.ok_or_data("break-exec $8F23")
                client.ok("key 89")  # Y
                client.ok("wait-paused 15000")
                if cpu_pc(client.ok("get-cpu")) != 0x8F23:
                    raise RuntimeError("Y did not reach save call")
                print(f"save retry: $8F23 {client.ok('get-cpu')}", flush=True)
                points.append({"label": "save retry", "pc": "0x8F23",
                               "cpu": client.ok("get-cpu"), "state": client.ok("get-state")})
                points.append(wait_at(client, "save call return", (0x8F2C,)))
                carry = status_carry(points[-1]["cpu"])
                print(f"save call carry set: {carry}", flush=True)
                points.append(wait_at(client, "post-save branch", (0x895B, 0x8F31)))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    if describe(original_disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("original game disk changed")
    if describe(PLAYER) != blank_player:
        raise RuntimeError("blank player disk template changed")
    final = OUTPUT / "saved.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "boot_media": media,
              "blank_player_disk": {"path": str(PLAYER), **blank_player},
              "working_player_disk": {"path": str(working_player),
                                      **describe(working_player)},
              "input": [{"key_ascii": 78, "at_pc": "0x8F9A"},
                        {"key_ascii": 89, "at_pc": "0x8F12"}],
              "checkpoints": points, "save_carry_set": carry,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"GEN player-save trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
