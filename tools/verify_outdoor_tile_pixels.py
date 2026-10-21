#!/usr/bin/env python3
"""Verify one outdoor tile's RAM, video, and retained-frame pixel effect."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
REPORT = ROOT / "build/traces/outdoor-tile-pixels/handoff.json"
EXPECTED_VIDEO = (0x4081, 0x4101, 0x4102, 0x4481, 0x4482, 0x4502,
                  0x4881, 0x4901, 0x4C81, 0x4D01, 0x5081, 0x5101,
                  0x5482, 0x5501, 0x5502, 0x5881, 0x5882, 0x5901,
                  0x5C81, 0x5C82)


def checked(item):
    path = Path(item["path"])
    assert describe(path) == {"size": item["size"], "sha256": item["sha256"]}
    return main_ram(path)


def main():
    if not REPORT.is_file():
        print("PENDING outdoor tile pixel trace; run tools/run_runtime.py trace_outdoor_tile_pixels.py")
        return 0
    source = json.loads(SOURCE.read_text())
    report = json.loads(REPORT.read_text())
    assert report["source_snapshot"] == source["snapshot"]
    assert report["working_game_disk"] == source["working_game_disk"]
    checked(report["source_snapshot"])
    disk = report["working_game_disk"]
    assert describe(Path(disk["path"])) == {"size": disk["size"],
                                             "sha256": disk["sha256"]}
    assert report["target"] == "$675E"
    trials = report["trials"]
    assert tuple(trials) == ("original", "tile04", "tile00", "tile06", "tile08",
                             "tile0A", "tile0C", "tile0E", "lowbit03", "highbit82")
    ram = {}
    for name, value in (("original", None), ("tile04", 4), ("tile00", 0),
                        ("tile06", 6), ("tile08", 8), ("tile0A", 10),
                        ("tile0C", 12), ("tile0E", 14),
                        ("lowbit03", 3), ("highbit82", 0x82)):
        trial = trials[name]
        ram[name] = checked(trial["snapshot"])
        assert trial["entry"]["pc"] == trial["next_entry"]["pc"] == "0x1C39"
        assert trial["return"]["pc"] == trial["next_return"]["pc"] == "0x1DA6"
        assert trial["frame"]["number"] == 2834
        assert (trial["frame"]["width"], trial["frame"]["height"],
                trial["frame"]["stride"], trial["frame"]["format"]) == \
               (560, 192, 2240, "argb8888")
        if value is None:
            assert trial["tile_intervention"] is None
        else:
            assert trial["tile_intervention"] == {
                "address": "$675E", "before": "$02", "after": f"${value:02X}",
                "restored_at": "$1DA6"}
        assert ram[name][0x675E] == 2
        assert Path(trial["image"]).is_file()
    original, changed = ram["original"], ram["tile04"]
    differing = [address for address, (a, b) in enumerate(zip(original, changed))
                 if a != b]
    assert differing == list(EXPECTED_VIDEO)
    assert report["main_ram_changed_addresses"] == [f"${x:04X}" for x in differing]
    assert [int(item["address"][1:], 16) for item in report["video_changes"]] == \
           list(EXPECTED_VIDEO)
    assert report["pixel_changed_count"] == 158
    assert report["pixel_bounds"] == [14, 8, 39, 22]
    assert report["color_pairs"] == [
        ["000000ff", "00cb38ff"], ["000000ff", "ffffffff"],
        ["00cb38ff", "000000ff"]]
    assert report["color_pair_counts"] == [
        {"before": "000000ff", "after": "00cb38ff", "count": 140},
        {"before": "000000ff", "after": "ffffffff", "count": 10},
        {"before": "00cb38ff", "after": "000000ff", "count": 8}]
    assert trials["original"]["frame"]["sha256"] != \
           trials["tile04"]["frame"]["sha256"]
    assert trials["original"]["video_sha256"] != trials["tile04"]["video_sha256"]
    for name in ("lowbit03", "highbit82"):
        assert ram[name] == original
        assert report["controls"][name] == {
            "video_matches_original": True, "pixels_match_original": True,
            "main_ram_matches_original": True}
        assert trials[name]["frame"]["sha256"] == trials["original"]["frame"]["sha256"]
    expected_terrain = {
        "tile00": (32, 106, [14, 8, 41, 23]),
        "tile04": (20, 158, [14, 8, 39, 22]),
        "tile06": (31, 146, [14, 8, 43, 23]),
        "tile08": (28, 272, [14, 8, 41, 22]),
        "tile0A": (28, 170, [14, 8, 41, 22]),
        "tile0C": (16, 146, [14, 10, 41, 19]),
        "tile0E": (32, 152, [14, 8, 43, 23]),
    }
    assert tuple(report["terrain"]) == tuple(expected_terrain)
    for name, (video_count, pixel_count, bounds) in expected_terrain.items():
        effect = report["terrain"][name]
        assert (effect["video_changed_count"], effect["pixel_changed_count"],
                effect["pixel_bounds"]) == (video_count, pixel_count, bounds)
        assert sum(pair["count"] for pair in effect["color_pair_counts"]) == pixel_count
        assert ram[name][0x675E] == 2
        differing = [address for address, (a, b) in
                     enumerate(zip(original, ram[name])) if a != b]
        assert len(differing) == video_count
        assert all(0x4000 <= address < 0x6000 for address in differing)
        assert trials[name]["frame"]["sha256"] != trials["original"]["frame"]["sha256"]
    print("OUT one-tile $02->$04: 20 video bytes, 158 pixels within x14-39/y8-22")
    print("$03 and $82 controls match $02 after the renderer's $7E mask")
    print("seven alternate terrain codes compared at one viewport position")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AssertionError, ValueError, KeyError, TypeError) as error:
        print(f"outdoor tile pixel verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
