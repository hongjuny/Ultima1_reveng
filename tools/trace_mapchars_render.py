#!/usr/bin/env python3
"""Trace MAPCHARS swapping and the castle's first map glyph render."""

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
OUTPUT = ROOT / "build/traces/mapchars-render"


def sample(client, label):
    chars = (ROOT / "extracted/MAPCHARS").read_bytes()
    return {"label": label, "cpu": client.ok("get-cpu"),
            "font_0800_matches_mapchars": client.mem(0x0800, 1024) == chars,
            "font_b000_matches_mapchars": client.mem(0xB000, 1024) == chars,
            "renderer_operand": client.mem(0x1A58, 3).hex(),
            "video_2000_sha256": hashlib.sha256(client.mem(0x2000, 8192)).hexdigest()}


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
    final = OUTPUT / "first-input.a2state"
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
                    raise RuntimeError("restored castle map-copy return differs")
                client.ok("set-turbo 8")
                checkpoints = []
                for label, address in (("map render", 0x9B06),
                                       ("before swap", 0x9B09),
                                       ("after swap", 0x9B0C),
                                       ("first glyph", 0x1A58),
                                       ("before restore", 0x9B35),
                                       ("after restore", 0x9B38),
                                       ("first input", 0x8A27)):
                    wait_at(client, label, (address,))
                    checkpoints.append(sample(client, label))
                    print(f"{label}: PC ${address:04X}, MAPCHARS at "
                          f"0800={checkpoints[-1]['font_0800_matches_mapchars']} "
                          f"B000={checkpoints[-1]['font_b000_matches_mapchars']}", flush=True)
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "checkpoints": checkpoints, "final_cpu": client.ok("get-cpu"),
                          "snapshot": {"path": str(final), **describe(final)}}
            finally:
                client.s.close()
        finally:
            stop(process)
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"MAPCHARS render trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
