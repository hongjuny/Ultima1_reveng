#!/usr/bin/env python3
"""Verify the private finale PNG against NIF's complete HGR color raster."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_tm_nif_color import OUTPUT, SOURCE
from trace_tm_nif_render import hgr_offset
from verify_outdoor_hgr_palette import expected_column, read_rgb_png


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING TM NIF color trace")
        return 0
    report = json.loads(path.read_text())
    prior = json.loads(SOURCE.read_text())
    require(report["source_snapshot"] == prior["trials"]["intact"]["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "NIF color source ancestry changed")
    for item in (report["source_snapshot"], report["working_game_disk"],
                 report["frame"]["private_png"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private input or frame changed")
    nif = (ROOT / "extracted/NIF").read_bytes()
    require(len(nif) == 7680 and
            report["nif_sha256"] == hashlib.sha256(nif).hexdigest(),
            "NIF source changed")
    require(report["cpu"].startswith("pc=9132") and
            report["video_switches"] == {"TEXT": 0, "MIXED": 0,
                                         "PAGE2": 0, "HIRES": 1},
            "finale video mode differs")
    frame = report["frame"]
    require((frame["width"], frame["height"], frame["stride"], frame["format"]) ==
            (560, 192, 2240, "argb8888"), "finale frame geometry differs")
    ram = bytearray(0x6000)
    for y in range(192):
        off = hgr_offset(y)
        ram[0x4000 + off:0x4000 + off + 40] = nif[y * 40:(y + 1) * 40]
    raw, row_size = read_rgb_png(Path(frame["private_png"]["path"]))
    colors = set()
    for y in range(192):
        row = raw[y * row_size + 1:(y + 1) * row_size]
        for col in range(40):
            for i, expected in enumerate(expected_column(ram, y, col)):
                x = col * 14 + i
                actual = int.from_bytes(row[x * 3:x * 3 + 3], "big")
                require(actual == expected, f"NIF pixel ({x},{y}) differs")
                colors.add(actual)
    require(report["comparison"] == {
        "matching_pixels": 107520, "total_pixels": 107520,
        "first_difference": None,
        "observed_colors": [f"${color:06X}" for color in sorted(colors)]},
        "NIF color comparison report differs")
    require(colors == {0x000000, 0x0DA1FF, 0xF25E00, 0xFFFFFF},
            "NIF final color set differs")
    print("TM NIF color: all 107520 finale pixels match HGR bytes and "
          "four-color emulator palette")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AssertionError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF color verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
