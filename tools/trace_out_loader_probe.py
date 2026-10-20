#!/usr/bin/env python3
"""Locate where the OUT overlay load stalls after the disk swap."""

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
OUTPUT = ROOT / "build" / "traces" / "out-loader-probe"


def current_path(client) -> str:
    length = client.mem(0xBA79, 1)[0]
    if length > 63:
        return f"invalid length {length}"
    return client.mem(0xBA7A, length).decode("ascii", errors="replace")


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("GEN-to-OUT source snapshot differs")
    player_item = prior["player_disk"]
    player_disk = Path(player_item["path"])
    if describe(player_disk) != {"size": player_item["size"], "sha256": player_item["sha256"]}:
        raise RuntimeError("player disk differs")
    manifest = json.loads(MANIFEST.read_text())
    media = manifest["runtime"].get("boot_media") or manifest["disk_image"]
    game_disk = Path(media["path"])
    if describe(game_disk) != {"size": media["size"], "sha256": media["sha256"]}:
        raise RuntimeError("game disk differs from baseline")
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    working_game = OUTPUT / "game-probe.po"
    shutil.copyfile(game_disk, working_game)
    pending = OUTPUT / f"loader-stage.pending-{os.getpid()}.a2state"
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
                client.ok("set-turbo 8")
                client.ok("unmount kind=diskii 6 0")
                client.ok(f"mount-disk 6 0 {working_game}")
                points.append(wait_at(client, "OUT request", (0x8920,)))
                points.append(wait_at(client, "filename helper return", (0x8928,)))
                print(f"filename helper: {points[-1]['cpu']} path={current_path(client)!r} "
                      f"carry={status_carry(points[-1]['cpu'])}", flush=True)
                points.append(wait_at(client, "STUPH loader attempt",
                                      (0x16AD, 0x16B9, 0x16C1)))
                print(f"loader attempt: {points[-1]['cpu']} path={current_path(client)!r}",
                      flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = OUTPUT / "loader-stage.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "player_disk": player_item,
              "boot_media": media,
              "working_game_disk": {"path": str(working_game), **describe(working_game)},
              "checkpoints": points,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private probe: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT loader probe failed: {error}", file=sys.stderr)
        raise SystemExit(1)
