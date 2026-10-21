#!/usr/bin/env python3
"""Capture one castle glyph's source bytes and exact video RAM writes."""

import hashlib
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build/traces/tcmaps-last-slot/handoff.json"
OUTPUT = ROOT / "build/traces/mapchars-glyph-bytes"


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["trials"]["ordinary"]["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    OUTPUT.mkdir(parents=True, exist_ok=True)
    final = OUTPUT / "after-glyph.a2state"
    final.unlink(missing_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x89E0:
                    raise RuntimeError("restored castle map copy differs")
                client.ok("set-turbo 8")
                entry = wait_at(client, "first glyph source read", (0x1A58,))
                code = int(entry["cpu"].split(" y=")[1][:2], 16)
                font = client.mem(0x0800, 1024)
                chars = (ROOT / "extracted/MAPCHARS").read_bytes()
                if font != chars:
                    raise RuntimeError("MAPCHARS not live at glyph read")
                glyph = [font[row * 128 + code] for row in range(8)]
                renderer = client.mem(0x1A58, 11).hex()
                xor_byte = client.mem(0x7E, 1)[0]
                before = client.mem(0x2000, 0x4000, "main")
                frame_before = client.get_frame()
                exit_point = wait_at(client, "glyph done", (0x1A7F,))
                after = client.mem(0x2000, 0x4000, "main")
                frame_after = client.get_frame()
                changes = [{"address": f"0x{0x2000+i:04X}", "before": a,
                            "after": b} for i, (a, b) in enumerate(zip(before, after))
                           if a != b]
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "entry": entry, "exit": exit_point, "code": code,
                          "glyph_rows": glyph, "renderer_bytes": renderer,
                          "xor_byte": xor_byte, "changes": changes,
                          "frame_before": {"frame": frame_before["frame"],
                                           "sha256": hashlib.sha256(frame_before["pixels"]).hexdigest()},
                          "frame_after": {"frame": frame_after["frame"],
                                          "sha256": hashlib.sha256(frame_after["pixels"]).hexdigest()},
                          "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"glyph ${code:02X}, xor ${xor_byte:02X}, "
          f"changed video bytes {len(changes)}: "
          f"{[(x['address'], x['before'], x['after']) for x in changes[:16]]}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"MAPCHARS glyph trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
