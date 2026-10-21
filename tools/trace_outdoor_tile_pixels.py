#!/usr/bin/env python3
"""Compare one outdoor map tile against the same frame with one byte changed."""

import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

from baseline import MANIFEST, describe
from capture_boot import connect, launch, stop, wait_for_snapshot
from disassemble import ROOT
from trace_startup import cpu_pc, wait_at
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
OUTPUT = ROOT / "build/traces/outdoor-tile-pixels"
TARGET = 0x675E  # first viewport tile for player ($27,$21)
ORIGINAL = 0x02
REPLACEMENT = 0x04


def trial(emulator, disk, source, name, replacement):
    sys.path.insert(0, str(ROOT / "build/emulator/a2m/tools"))
    from a2m_control_client import Ctl, write_argb_png

    snapshot = OUTPUT / f"{name}.a2state"
    snapshot.unlink(missing_ok=True)
    with (OUTPUT / f"{name}.log").open("w") as log:
        process = launch(emulator, disk, None, log, inspector=True)
        try:
            client = connect(Ctl, process)
            try:
                client.ok("hello")
                client.ok("wait-paused 3000")
                client.ok(f"load-state {source['path']}")
                if cpu_pc(client.ok("get-cpu")) != 0x8A6C:
                    raise RuntimeError("source did not restore at OUT poll")
                client.ok("set-turbo 8")
                client.frame_ring_clear()
                client.frame_ring_record(True)
                entry = wait_at(client, f"{name} outdoor draw", (0x1C39,))
                if client.mem(0x0000, 2) != bytes((0x27, 0x21)):
                    raise RuntimeError("outdoor position changed")
                if client.mem(TARGET, 1) != bytes((ORIGINAL,)):
                    raise RuntimeError("target tile changed")
                if replacement is not None:
                    client.set_mem(TARGET, bytes((replacement,)))
                returned = wait_at(client, f"{name} draw return", (0x1DA6,))
                if replacement is not None:
                    client.set_mem(TARGET, bytes((ORIGINAL,)))
                video = client.mem(0x2000, 0x4000, "main")
                first_frame = client.get_frame()["frame"]
                client.ok(f"save-state {snapshot}")
                wait_for_snapshot(snapshot)
                second_entry = wait_at(client, f"{name} next draw", (0x1C39,))
                second_return = wait_at(client, f"{name} next draw return", (0x1DA6,))
                print(name, "ring", client.frame_ring_info(), flush=True)
                frame = client.get_frame_at(frame=first_frame + 1)
                image = OUTPUT / f"{name}.png"
                if not write_argb_png(str(image), frame["width"], frame["height"],
                                      frame["pixels"], stride=frame["stride"]):
                    raise RuntimeError("failed to write private frame PNG")
                return ({"entry": entry, "return": returned,
                         "next_entry": second_entry, "next_return": second_return,
                         "tile_intervention": None if replacement is None else
                         {"address": f"${TARGET:04X}", "before": f"${ORIGINAL:02X}",
                          "after": f"${replacement:02X}",
                          "restored_at": "$1DA6"},
                         "frame": {"width": frame["width"], "height": frame["height"],
                                   "stride": frame["stride"], "format": frame["format"],
                                   "number": frame["frame"],
                                   "sha256": hashlib.sha256(frame["pixels"]).hexdigest()},
                         "video_sha256": hashlib.sha256(video).hexdigest(),
                         "snapshot": {"path": str(snapshot), **describe(snapshot)},
                         "image": str(image)}, video, frame["pixels"])
            finally:
                client.s.close()
        finally:
            stop(process)


def main():
    prior = json.loads(SOURCE.read_text())
    if cpu_pc(prior["final_cpu"]) != 0x8A6C:
        raise RuntimeError("source report is not the first OUT poll")
    source, disk_item = prior["snapshot"], prior["working_game_disk"]
    for item in (source, disk_item):
        if describe(Path(item["path"])) != {"size": item["size"],
                                               "sha256": item["sha256"]}:
            raise RuntimeError("private input changed")
    original_ram = main_ram(Path(source["path"]))
    if original_ram[TARGET] != ORIGINAL:
        raise RuntimeError("source tile differs")
    emulator = Path(json.loads(MANIFEST.read_text())["runtime"]["emulator"]["path"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    runs = {name: trial(emulator, Path(disk_item["path"]), source, name, replacement)
            for name, replacement in (("original", None), ("tile04", REPLACEMENT),
                                      ("tile00", 0x00), ("tile06", 0x06),
                                      ("tile08", 0x08), ("tile0A", 0x0A),
                                      ("tile0C", 0x0C), ("tile0E", 0x0E),
                                      ("lowbit03", 0x03), ("highbit82", 0x82))}
    original, video_a, pixels_a = runs["original"]
    tile04, video_b, pixels_b = runs["tile04"]
    video_changes = [{"address": f"${0x2000+i:04X}", "before": f"${a:02X}",
                      "after": f"${b:02X}"}
                     for i, (a, b) in enumerate(zip(video_a, video_b)) if a != b]
    stride = original["frame"]["stride"]
    pixel_changes = []
    colors = Counter()
    for i in range(0, len(pixels_a), 4):
        a, b = pixels_a[i:i+4], pixels_b[i:i+4]
        if a != b:
            pixel_changes.append((i % stride // 4, i // stride))
            colors[(a.hex(), b.hex())] += 1
    bounds = ([min(x for x, _ in pixel_changes), min(y for _, y in pixel_changes),
               max(x for x, _ in pixel_changes), max(y for _, y in pixel_changes)]
              if pixel_changes else None)
    ram_a = main_ram(Path(original["snapshot"]["path"]))
    ram_b = main_ram(Path(tile04["snapshot"]["path"]))
    ram_changes = [f"${i:04X}" for i, (a, b) in enumerate(zip(ram_a, ram_b))
                   if a != b]
    controls = {}
    for name in ("lowbit03", "highbit82"):
        control, control_video, control_pixels = runs[name]
        control_ram = main_ram(Path(control["snapshot"]["path"]))
        controls[name] = {"video_matches_original": control_video == video_a,
                          "pixels_match_original": control_pixels == pixels_a,
                          "main_ram_matches_original": control_ram == ram_a}
    terrain = {}
    for name in ("tile00", "tile04", "tile06", "tile08", "tile0A", "tile0C", "tile0E"):
        _, tile_video, tile_pixels = runs[name]
        video_count = sum(a != b for a, b in zip(video_a, tile_video))
        pixel_positions = []
        color_counts = Counter()
        for i in range(0, len(pixels_a), 4):
            a, b = pixels_a[i:i+4], tile_pixels[i:i+4]
            if a != b:
                pixel_positions.append((i % stride // 4, i // stride))
                color_counts[(a.hex(), b.hex())] += 1
        terrain[name] = {
            "video_changed_count": video_count,
            "pixel_changed_count": len(pixel_positions),
            "pixel_bounds": ([min(x for x, _ in pixel_positions),
                              min(y for _, y in pixel_positions),
                              max(x for x, _ in pixel_positions),
                              max(y for _, y in pixel_positions)] if pixel_positions else None),
            "color_pair_counts": [{"before": a, "after": b, "count": n}
                                  for (a, b), n in sorted(color_counts.items())],
        }
    report = {"source_snapshot": source, "working_game_disk": disk_item,
              "target": f"${TARGET:04X}",
              "trials": {name: result[0] for name, result in runs.items()},
              "video_changes": video_changes,
              "pixel_changed_count": len(pixel_changes), "pixel_bounds": bounds,
              "color_pairs": sorted([list(pair) for pair in colors]),
              "color_pair_counts": [{"before": a, "after": b, "count": n}
                                    for (a, b), n in sorted(colors.items())],
              "main_ram_changed_addresses": ram_changes, "controls": controls,
              "terrain": terrain}
    path = OUTPUT / "handoff.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"one tile $02->$04: {len(video_changes)} video bytes, "
          f"{len(pixel_changes)} pixels; bounds={bounds}")
    print("color pairs:", report["color_pairs"])
    print("color counts:", report["color_pair_counts"])
    print("main RAM differences:", len(ram_changes), ram_changes[:40])
    print("masked-bit controls:", controls)
    print("terrain classes:", {name: (item["video_changed_count"],
                                      item["pixel_changed_count"], item["pixel_bounds"])
                               for name, item in terrain.items()})
    print("private trace:", path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, IndexError) as error:
        print(f"outdoor tile pixel trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
