#!/usr/bin/env python3
"""Swap back to a private game-disk copy and follow GEN into OUT."""

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


SOURCE = ROOT / "build" / "traces" / "gen-load-player" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "gen-to-out"


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("OUT-handoff snapshot differs from GEN B trace")
    player_item = prior["player_disk"]
    player_disk = Path(player_item["path"])
    if describe(player_disk) != {"size": player_item["size"], "sha256": player_item["sha256"]}:
        raise RuntimeError("player disk differs from GEN B trace")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    original_game = Path(media["path"])
    if describe(original_game) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("game disk differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    expected_out = (ROOT / "extracted" / "OUT").read_bytes()
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    working_game = OUTPUT / "game-working.po"
    shutil.copyfile(original_game, working_game)
    pending = OUTPUT / f"out-entry.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    points = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, player_disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x8AC0:
                    raise RuntimeError("snapshot is not at GEN's OUT handoff")
                if client.mem(0x7E1A, 4) != b"OUT\x00":
                    raise RuntimeError("OUT filename is absent from selector table")
                client.ok("set-turbo 8")
                client.ok("unmount kind=diskii 6 0")
                client.ok(f"mount-disk 6 0 {working_game}")
                points.append(wait_at(client, "outdoor selector", (0x88FB,)))
                points.append(wait_at(client, "OUT request", (0x8920,)))
                if client.mem(0x7E16, 4) != b"OUT\x00":
                    raise RuntimeError("selector did not install OUT filename")
                points.append(wait_at(client, "OUT loader return", (0x892E,)))
                if status_carry(points[-1]["cpu"]):
                    raise RuntimeError("OUT loader returned with carry set")
                actual = client.mem(0x8956, len(expected_out))
                if actual != expected_out:
                    first = next(i for i, (a, b) in enumerate(zip(actual, expected_out))
                                 if a != b)
                    raise RuntimeError(f"OUT differs at ${0x8956 + first:04X}")
                print(f"OUT: {len(expected_out)} bytes match at $8956", flush=True)
                points.append(wait_at(client, "OUT entry", (0x8956,)))
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    if describe(original_game) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("original game disk changed")
    if describe(player_disk) != {"size": player_item["size"], "sha256": player_item["sha256"]}:
        raise RuntimeError("player disk changed during OUT load")
    final = OUTPUT / "out-entry.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "player_disk": player_item,
              "boot_media": media,
              "working_game_disk": {"path": str(working_game), **describe(working_game)},
              "checkpoints": points, "out_bytes": len(expected_out),
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, StopIteration) as error:
        print(f"GEN-to-OUT trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
