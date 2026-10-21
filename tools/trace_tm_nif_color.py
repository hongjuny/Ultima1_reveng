#!/usr/bin/env python3
"""Capture the private finale frame and compare its HGR colors to NIF bytes."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop
from disassemble import ROOT
from trace_startup import cpu_pc
from trace_tm_nif_render import hgr_offset
from verify_outdoor_hgr_palette import expected_column


SOURCE = ROOT / "build/traces/tm-nif-tail-effect/handoff.json"
OUTPUT = ROOT / "build/traces/tm-nif-color"


def compare(frame, page):
    if (frame["width"], frame["height"], frame["format"]) != (560, 192, "argb8888"):
        raise RuntimeError("unexpected video frame format")
    ram = bytearray(0x6000)
    ram[0x4000:0x6000] = page
    matches = 0
    first_difference = None
    observed = set()
    for y in range(192):
        for col in range(40):
            expected = expected_column(ram, y, col)
            for local_x, color in enumerate(expected):
                x = col * 14 + local_x
                offset = y * frame["stride"] + x * 4
                b, g, r = frame["pixels"][offset:offset + 3]
                actual = (r << 16) | (g << 8) | b
                observed.add(actual)
                if actual == color:
                    matches += 1
                elif first_difference is None:
                    first_difference = {"x": x, "y": y,
                                        "actual": f"${actual:06X}",
                                        "expected": f"${color:06X}"}
    return {"matching_pixels": matches, "total_pixels": 560 * 192,
            "first_difference": first_difference,
            "observed_colors": [f"${color:06X}" for color in sorted(observed)]}


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["trials"]["intact"]["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    if cpu_pc(prior["trials"]["intact"]["final_cpu"]) != 0x9132:
        raise RuntimeError("source is not at finale key wait")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl, write_argb_png
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "a2m.log").open("w") as log:
        process = launch(emulator, Path(disk_item["path"]), None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x9132:
                    raise RuntimeError("restored finale PC differs")
                page = client.mem(0x2000, 8192)
                packed = (ROOT / "extracted/NIF").read_bytes()
                if any(page[hgr_offset(y):hgr_offset(y) + 40] != packed[y * 40:(y + 1) * 40]
                       for y in range(192)):
                    raise RuntimeError("final HGR page 1 differs from NIF")
                frame = client.get_frame()
                png = OUTPUT / "final-frame.png"
                if not write_argb_png(str(png), frame["width"], frame["height"],
                                      frame["pixels"], stride=frame["stride"]):
                    raise RuntimeError("could not write private frame")
                result = compare(frame, page)
                switches = client.get_softswitches()
                report = {"source_snapshot": source, "working_game_disk": disk_item,
                          "cpu": client.ok("get-cpu"),
                          "video_switches": {key: switches[key]
                                             for key in ("TEXT", "MIXED", "PAGE2", "HIRES")},
                          "nif_sha256": hashlib.sha256(packed).hexdigest(),
                          "frame": {"number": frame["frame"], "width": frame["width"],
                                    "height": frame["height"], "stride": frame["stride"],
                                    "format": frame["format"],
                                    "sha256": hashlib.sha256(frame["pixels"]).hexdigest(),
                                    "private_png": {"path": str(png), **describe(png)}},
                          "comparison": result}
            finally:
                client.s.close()
        finally:
            stop(process)
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print("NIF finale frame:", result, flush=True)
    print("video switches:", report["video_switches"], flush=True)
    print("private trace:", path)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF color trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
