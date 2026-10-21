#!/usr/bin/env python3
"""Compare the first castle glyph with only its eight live font bytes blanked."""

import hashlib
import json
from pathlib import Path
import sys
import time

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/tcmaps-last-slot/handoff.json"
OUTPUT = ROOT / "build/traces/mapchars-single-glyph"
CODE = 0x40


def trial(emulator, disk, source, name, replacement, output):
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl
    final = output / f"{name}.a2state"
    final.unlink(missing_ok=True)
    with (output / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x89E0:
                    raise RuntimeError("restored castle map copy differs")
                client.ok("set-turbo 8")
                entry = wait_at(client, f"{name} first glyph", (0x1A58,))
                addresses = [0x0800 + row * 128 + CODE for row in range(8)]
                original = [client.mem(address, 1)[0] for address in addresses]
                if replacement is not None:
                    for address in addresses:
                        client.set_mem(address, bytes([replacement]))
                exit_point = wait_at(client, f"{name} glyph return", (0x1A7F,))
                if replacement is not None:
                    for address, value in zip(addresses, original):
                        client.set_mem(address, bytes([value]))
                poll = wait_at(client, f"{name} castle poll", (0x8A27,))
                frame = client.get_frame()
                client.ok(f"save-state {final}")
                wait_for_snapshot(final)
                time.sleep(0.2)
                return ({"intervention": None if replacement is None else
                         {"addresses": [f"0x{x:04X}" for x in addresses],
                          "value": f"{replacement:02X}", "restored_at": "0x1A7F"},
                         "glyph_before": original,
                         "checkpoints": [entry, exit_point, poll],
                         "frame": {"width": frame["width"],
                                   "height": frame["height"],
                                   "stride": frame["stride"],
                                   "format": frame["format"],
                                   "number": frame["frame"],
                                   "sha256": hashlib.sha256(frame["pixels"]).hexdigest()},
                         "final_cpu": client.ok("get-cpu"),
                         "snapshot": {"path": str(final), **describe(final)}},
                        frame["pixels"])
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())
    source = prior["trials"]["ordinary"]["snapshot"]
    disk_item = prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"], "sha256": item["sha256"]}:
            raise RuntimeError(f"private input changed: {item['path']}")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trials_with_pixels = {
        name: trial(emulator, Path(disk_item["path"]), source, name, value, OUTPUT)
        for name, value in (("original", None), ("blank", 0x80),
                            ("bit0", 0x81), ("bit6", 0xC0),
                            ("phase0", 0x00), ("phase0_bit0", 0x01))
    }
    original, pixels_a = trials_with_pixels["original"]
    blank, pixels_b = trials_with_pixels["blank"]
    ram_a = main_ram(Path(original["snapshot"]["path"]))
    ram_b = main_ram(Path(blank["snapshot"]["path"]))
    differences = [{"address": f"0x{i:04X}", "original": a, "blank": b}
                   for i, (a, b) in enumerate(zip(ram_a, ram_b)) if a != b]
    if len(pixels_a) != len(pixels_b):
        raise RuntimeError("frame sizes differ")
    pixel_byte_changes = sum(a != b for a, b in zip(pixels_a, pixels_b))
    stride = original["frame"]["stride"]
    changed_pixels = []
    colors = set()
    for offset in range(0, len(pixels_a), 4):
        first = pixels_a[offset:offset+4]
        second = pixels_b[offset:offset+4]
        if first != second:
            changed_pixels.append([offset % stride // 4, offset // stride])
            colors.add((first.hex(), second.hex()))
    bounds = ([min(p[0] for p in changed_pixels),
               min(p[1] for p in changed_pixels),
               max(p[0] for p in changed_pixels),
               max(p[1] for p in changed_pixels)] if changed_pixels else None)
    pattern_effects = {}
    for name, (trial_report, pixels) in trials_with_pixels.items():
        if name in ("original", "blank"):
            continue
        changed = []
        color_pairs = set()
        for offset in range(0, len(pixels), 4):
            a = pixels[offset:offset+4]
            b = pixels_b[offset:offset+4]
            if a != b:
                changed.append([offset % stride // 4, offset // stride])
                color_pairs.add((a.hex(), b.hex()))
        pattern_effects[name] = {
            "pixel_count": len(changed),
            "bounds": ([min(p[0] for p in changed), min(p[1] for p in changed),
                        max(p[0] for p in changed), max(p[1] for p in changed)]
                       if changed else None),
            "color_pairs_against_blank": sorted([list(x) for x in color_pairs]),
        }
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "trials": {name: trial_report for name, (trial_report, _)
                         in trials_with_pixels.items()},
              "main_ram_differences": differences,
              "frame_byte_differences": pixel_byte_changes,
              "frame_pixel_differences": len(changed_pixels),
              "frame_bounds": bounds,
              "frame_color_pairs": sorted([list(x) for x in colors]),
              "pattern_effects": pattern_effects}
    (OUTPUT / "handoff.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"single glyph: {len(differences)} RAM bytes, "
          f"{pixel_byte_changes} frame bytes / {len(changed_pixels)} pixels "
          f"differ; bounds={bounds}; colors={report['frame_color_pairs']}")
    print(differences[:16])
    for name, effect in pattern_effects.items():
        print(f"{name}: {effect}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"MAPCHARS single-glyph trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
