#!/usr/bin/env python3
"""Trace one outdoor text glyph from the shared loop into video memory."""

import hashlib
import json
import os
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at


SOURCE = ROOT / "build" / "traces" / "out-space-effect" / "handoff.json"
OUTPUT = ROOT / "build" / "traces" / "out-render-pipeline"
CHECKPOINTS = (
    ("outdoor frame", 0x8995),
    ("inline text", 0x8119),
    ("character output", 0x8062),
    ("STUPH character vector", 0x15B0),
    ("video renderer", 0x1A1D),
    ("character return", 0x8065),
    ("outdoor loop", 0x89A1),
    ("shared status", 0x836E),
    ("next outdoor poll", 0x8A6C),
)


def video(client) -> bytes:
    return client.mem(0x2000, 0x4000, "main")


def frame_digest(client) -> dict:
    frame = client.get_frame()
    return {"width": frame["width"], "height": frame["height"],
            "frame": frame["frame"],
            "sha256": hashlib.sha256(frame["pixels"]).hexdigest()}


def main() -> int:
    prior = json.loads(SOURCE.read_text())
    if prior["timeout"] is not None or cpu_pc(prior["final_cpu"]) != 0x89DF:
        raise RuntimeError("source is not the completed outdoor Space handler")
    source = prior["snapshot"]
    snapshot = Path(source["path"])
    if describe(snapshot) != {"size": source["size"], "sha256": source["sha256"]}:
        raise RuntimeError("source snapshot differs")
    disk_item = prior["working_game_disk"]
    disk = Path(disk_item["path"])
    if describe(disk) != {"size": disk_item["size"], "sha256": disk_item["sha256"]}:
        raise RuntimeError("working game disk differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build" / "emulator" / "a2m" / "tools"))
    from a2m_control_client import Ctl

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT / f"render.pending-{os.getpid()}.a2state"
    pending.unlink(missing_ok=True)
    checkpoints = []
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {snapshot}")
                if cpu_pc(client.ok("get-cpu")) != 0x89DF:
                    raise RuntimeError("source snapshot did not restore at $89DF")
                client.ok("set-turbo 8")
                for label, address in CHECKPOINTS[:3]:
                    checkpoints.append(wait_at(client, label, (address,)))
                character = client.ok("get-cpu")
                before = video(client)
                frame_before = frame_digest(client)
                for label, address in CHECKPOINTS[3:6]:
                    checkpoints.append(wait_at(client, label, (address,)))
                after = video(client)
                frame_after = frame_digest(client)
                changed = [0x2000 + i for i, (a, b) in enumerate(zip(before, after)) if a != b]
                print(f"character A={character.split(' a=')[1][:2]}; "
                      f"video bytes changed={len(changed)}; first={[hex(x) for x in changed[:12]]}", flush=True)
                for label, address in CHECKPOINTS[6:]:
                    checkpoints.append(wait_at(client, label, (address,)))
                frame_next_poll = frame_digest(client)
                client.ok(f"save-state {pending}")
                wait_for_snapshot(pending)
                final_cpu = client.ok("get-cpu")
            finally:
                client.s.close()
        finally:
            stop(process)
    final = OUTPUT / "render.a2state"
    pending.replace(final)
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "checkpoints": checkpoints, "character_cpu": character,
              "video_before_sha256": hashlib.sha256(before).hexdigest(),
              "video_after_sha256": hashlib.sha256(after).hexdigest(),
              "changed_video_addresses": [f"${x:04X}" for x in changed],
              "frame_before": frame_before, "frame_after": frame_after,
              "frame_next_poll": frame_next_poll,
              "final_cpu": final_cpu,
              "snapshot": {"path": str(final), **describe(final)}}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"private trace: {path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, IndexError) as error:
        print(f"OUT render pipeline trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
