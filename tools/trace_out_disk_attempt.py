#!/usr/bin/env python3
"""Observe the OUT disk fallback result and STUPH loader return."""

import argparse
import json
import os
from pathlib import Path
import struct
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-ram-attempt" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-disk-attempt"
HEAD_OUTPUT = ROOT / "build" / "traces" / "out-head-position"
PLAYER_SOURCE = ROOT / "build" / "traces" / "gen-load-player" / "handoff.json"


def pathname(client) -> str:
    count = client.mem(0xBA79, 1)[0]
    if count > 63:
        return f"invalid length {count}"
    return client.mem(0xBA7A, count).decode("ascii", errors="replace")


def drive_head_offset(snapshot: bytes) -> int:
    """Locate drive 0's quarter-track field in an a2m v2 DSKs chunk."""
    if len(snapshot) < 32 or snapshot[:4] != b"TS2A":
        raise ValueError("not an a2m v2 snapshot")
    offset = 32
    while offset + 8 <= len(snapshot):
        tag = snapshot[offset:offset + 4]
        length = struct.unpack_from("<I", snapshot, offset + 4)[0]
        start = offset + 8
        end = start + length
        if end > len(snapshot):
            raise ValueError("truncated snapshot chunk")
        if tag == b"DSKs":
            if snapshot[start] != 6 or snapshot[start + 1] != 0:
                raise ValueError("expected Disk II slot 6, drive 0")
            cursor = start + 10  # slot, active drive, controller cycle count
            image_count = struct.unpack_from("<H", snapshot, cursor)[0]
            cursor += 2
            if image_count != 1:
                raise ValueError("expected one mounted drive 0 image")
            for _ in range(image_count):
                name_length = struct.unpack_from("<H", snapshot, cursor)[0]
                cursor += 2 + name_length
            head = cursor + 35  # motor, head timer, and phase fields
            if head + 2 > end:
                raise ValueError("truncated drive mechanism")
            return head
        offset = end
    raise ValueError("snapshot has no Disk II state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preserve-head", action="store_true",
                        help="restore pre-swap head position in a private snapshot")
    args = parser.parse_args()
    output = HEAD_OUTPUT if args.preserve_head else OUTPUT
    prior = json.loads(SOURCE.read_text())
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("disk-fallback snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    manifest = json.loads(MANIFEST.read_text())
    emulator = Path(manifest["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    output.mkdir(parents=True, exist_ok=True)
    head_probe = None
    if args.preserve_head:
        player_item = json.loads(PLAYER_SOURCE.read_text())["snapshot"]
        player_path = Path(player_item["path"])
        if describe(player_path) != {"size": player_item["size"],
                                     "sha256": player_item["sha256"]}:
            raise RuntimeError("pre-swap player snapshot differs")
        source_bytes = snapshot.read_bytes()
        player_bytes = player_path.read_bytes()
        source_offset = drive_head_offset(source_bytes)
        player_offset = drive_head_offset(player_bytes)
        current = struct.unpack_from("<h", source_bytes, source_offset)[0]
        preserved = struct.unpack_from("<h", player_bytes, player_offset)[0]
        if not 0 <= current < 140 or not 0 <= preserved < 140 or current == preserved:
            raise RuntimeError(f"unexpected head positions: game={current}, player={preserved}")
        modified = bytearray(source_bytes)
        struct.pack_into("<h", modified, source_offset, preserved)
        snapshot = output / "head-preserved.a2state"
        snapshot.write_bytes(modified)
        head_probe = {"player_snapshot": player_item,
                      "game_quarter_track": current,
                      "preserved_quarter_track": preserved,
                      "patched_snapshot": {"path": str(snapshot), **describe(snapshot)}}
        print(f"Disk II head: game mount {current} → pre-swap {preserved}", flush=True)
    pending = output / f"disk-result.pending-{os.getpid()}.a2state"
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
                if cpu_pc(client.ok("get-cpu")) != 0x16B9:
                    raise RuntimeError("snapshot is not at OUT disk fallback")
                if client.mem(0x1709, 4) != b"OUT\x00":
                    raise RuntimeError("disk fallback filename is not relative OUT")
                client.ok("set-turbo 8")
                try:
                    points.append(wait_at(client, "OUT disk read return", (0x16C8,)))
                    print(f"disk read: carry={status_carry(points[-1]['cpu'])} "
                          f"path={pathname(client)!r} {points[-1]['cpu']}", flush=True)
                    points.append(wait_at(client, "loader result", (0x16FC,)))
                    print(f"loader result: carry={status_carry(points[-1]['cpu'])} "
                          f"{points[-1]['cpu']}", flush=True)
                    points.append(wait_at(client, "OUT load caller return", (0x892B,)))
                    print(f"caller return: carry={status_carry(points[-1]['cpu'])} "
                          f"{points[-1]['cpu']}", flush=True)
                except RuntimeError as error:
                    timeout = str(error)
                    print(f"disk fallback stopped before expected return: {timeout}",
                          flush=True)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
                final_state = client.ok("get-state")
                final_path = pathname(client)
            finally:
                client.s.close()
        finally:
            stop(process)

    final = output / "disk-result.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "head_probe": head_probe,
              "checkpoints": points, "timeout": timeout,
              "final_cpu": final_cpu, "final_state": final_state,
              "final_path": final_path,
              "snapshot": {"path": str(final), **describe(final)}}
    path = output / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private probe: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT disk-attempt trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
