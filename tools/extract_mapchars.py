#!/usr/bin/env python3
"""Decode MAPCHARS' 128 glyphs in eight scanline planes, locally only."""

import argparse
import hashlib
import json

from disassemble import ROOT


SOURCE = ROOT / "extracted/MAPCHARS"
OUTPUT = ROOT / "build/data/MAPCHARS/glyphs.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()
    data = SOURCE.read_bytes()
    if len(data) != 1024:
        raise SystemExit(f"MAPCHARS: expected 1024 bytes, got {len(data)}")
    glyphs = [[data[row * 128 + code] for row in range(8)]
              for code in range(128)]
    rebuilt = bytes(glyphs[code][row] for row in range(8) for code in range(128))
    if rebuilt != data:
        raise SystemExit("MAPCHARS scanline-plane round trip differs")
    if not args.check:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps({
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "layout": "8 scanline planes × 128 character codes; raw 8-bit values",
            "glyphs": glyphs,
        }, indent=2) + "\n")
        print(f"private glyph data: {OUTPUT}")
    print("MAPCHARS: 128 glyphs × 8 scanline bytes; byte-exact round trip")


if __name__ == "__main__":
    main()
