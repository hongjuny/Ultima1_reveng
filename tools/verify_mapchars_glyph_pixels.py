#!/usr/bin/env python3
"""Verify one glyph's video bytes and paired pixel-level controls."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private glyph snapshot changed: {path}")
    return main_ram(path)


def main():
    if not (TRACE / "mapchars-single-glyph/handoff.json").is_file():
        print("PENDING MAPCHARS glyph pixel controls")
        return 0
    source = json.loads((TRACE / "tcmaps-last-slot/handoff.json").read_text())
    glyph = json.loads((TRACE / "mapchars-glyph-bytes/handoff.json").read_text())
    pair = json.loads((TRACE / "mapchars-single-glyph/handoff.json").read_text())
    initial = source["trials"]["ordinary"]["snapshot"]
    require(glyph["source_snapshot"] == pair["source_snapshot"] == initial and
            glyph["working_game_disk"] == pair["working_game_disk"] ==
            source["working_game_disk"], "MAPCHARS glyph source differs")
    chars = (ROOT / "extracted/MAPCHARS").read_bytes()
    require(glyph["entry"]["pc"] == "0x1A58" and
            glyph["exit"]["pc"] == "0x1A7F" and
            glyph["code"] == 0x40 and
            glyph["glyph_rows"] == [chars[row * 128 + 0x40] for row in range(8)] ==
            [0xFF] * 8 and glyph["xor_byte"] == 0 and
            glyph["renderer_bytes"] == "b90008457e8d81208d8120" and
            glyph["frame_before"] == glyph["frame_after"] and
            [x["address"] for x in glyph["changes"]] ==
            [f"0x{0x2081 + 0x400 * row:04X}" for row in range(8)] and
            [x["after"] for x in glyph["changes"]] == [255] * 8,
            "MAPCHARS first glyph read or immediate video writes differ")
    checked(glyph["snapshot"])

    trials = pair["trials"]
    expected_names = ("original", "blank", "bit0", "bit6", "phase0", "phase0_bit0")
    require(tuple(trials) == expected_names and
            pair["frame_pixel_differences"] == 112 and
            pair["frame_bounds"] == [14, 8, 27, 15] and
            pair["frame_color_pairs"] == [["ffffffff", "000000ff"]] and
            pair["frame_byte_differences"] == 336,
            "MAPCHARS first glyph frame bounds differ")
    ram = {}
    for name in expected_names:
        trial = trials[name]
        ram[name] = checked(trial["snapshot"])
        require([p["pc"] for p in trial["checkpoints"]] ==
                ["0x1A58", "0x1A7F", "0x8A27"] and
                trial["glyph_before"] == [255] * 8 and
                trial["final_cpu"].startswith("pc=8A27") and
                trial["frame"]["width"] == 560 and
                trial["frame"]["height"] == 192 and
                trial["frame"]["stride"] == 2240 and
                trial["frame"]["format"] == "argb8888" and
                trial["frame"]["number"] == 3396,
                f"MAPCHARS {name} trial differs")
    expected_addresses = [f"0x{0x2081 + 0x400 * row:04X}" for row in range(8)]
    require([x["address"] for x in pair["main_ram_differences"]] ==
            expected_addresses and
            [x["original"] for x in pair["main_ram_differences"]] == [255] * 8 and
            [x["blank"] for x in pair["main_ram_differences"]] == [128] * 8,
            "MAPCHARS paired video bytes differ")
    for name, value in (("original", 255), ("blank", 128), ("bit0", 129),
                        ("bit6", 192), ("phase0", 0), ("phase0_bit0", 1)):
        require([ram[name][0x2081 + 0x400 * row] for row in range(8)] ==
                [value] * 8,
                f"MAPCHARS {name} video value differs")
    effects = pair["pattern_effects"]
    require(effects["bit0"]["pixel_count"] == 16 and
            effects["bit0"]["bounds"] == [14, 8, 15, 15] and
            effects["bit6"]["pixel_count"] == 16 and
            effects["bit6"]["bounds"] == [26, 8, 27, 15] and
            effects["phase0"]["pixel_count"] == 0 and
            effects["phase0_bit0"]["pixel_count"] == 16 and
            effects["phase0_bit0"]["bounds"] == [14, 8, 15, 15],
            "MAPCHARS bit order or sampled high-bit effect differs")
    print("MAPCHARS $40: eight $FF rows write $2081,$2481,…,$3C81")
    print("first glyph: bits 0/6 occupy left/right two pixels in a 14×8 frame box")
    print("sampled high-bit change alone leaves this frame unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"MAPCHARS glyph-pixel verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
