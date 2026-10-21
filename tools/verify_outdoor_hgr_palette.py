#!/usr/bin/env python3
"""Recompute outdoor HGR pixels from saved page-two RAM and compare PNG frames.

The 3-bit color-window rule and palette come from the local a2m video renderer.
This verifies that the frame-ring observation follows from the saved Apple II
video bytes, including the first two pixels of the neighboring byte.
"""

import json
from pathlib import Path
import struct
import sys
import zlib

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram


REPORT = ROOT / "build/traces/outdoor-tile-pixels/handoff.json"
HGR_PALETTE = (
    0x000000, 0x000000, 0xC734FF, 0xFFFFFF,
    0x000000, 0x38CB00, 0xFFFFFF, 0xFFFFFF,
    0x000000, 0x000000, 0x0DA1FF, 0xFFFFFF,
    0x000000, 0xF25E00, 0xFFFFFF, 0xFFFFFF,
)


def read_rgb_png(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    chunks = []
    width = height = None
    while offset < len(data):
        size = int.from_bytes(data[offset:offset + 4], "big")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = int.from_bytes(data[offset + 8 + size:offset + 12 + size], "big")
        assert zlib.crc32(kind + payload) & 0xFFFFFFFF == crc
        offset += size + 12
        if kind == b"IHDR":
            width, height, depth, color, _, _, _ = struct.unpack(">IIBBBBB", payload)
            assert (width, height, depth, color) == (560, 192, 8, 2)
        elif kind == b"IDAT":
            chunks.append(payload)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(b"".join(chunks))
    row_size = width * 3 + 1
    assert len(raw) == row_size * height
    assert all(raw[y * row_size] == 0 for y in range(height))
    return raw, row_size


def hgr_row_offset(y):
    return ((y & 7) << 10) + (((y >> 3) & 7) << 7) + ((y >> 6) * 40)


def expected_column(ram, y, col):
    address = 0x4000 + hgr_row_offset(y) + col
    previous, current, following = ram[address - 1:address + 2]
    stream = ((following & 1) << 8) | ((current & 0x7F) << 1) | \
             ((previous >> 6) & 1)
    phase = (current >> 7) & 1
    pixels = []
    for bit in range(7):
        window = stream & 7
        if (col + bit) & 1 and window in (2, 5):
            window ^= 7
        pixels.extend((HGR_PALETTE[window + phase * 8],) * 2)
        stream >>= 1
    return pixels


def main():
    if not REPORT.is_file():
        print("PENDING outdoor HGR frame comparison")
        return 0
    report = json.loads(REPORT.read_text())
    trials = report["trials"]
    total = 0
    for name, trial in trials.items():
        item = trial["snapshot"]
        snapshot = Path(item["path"])
        assert describe(snapshot) == {"size": item["size"], "sha256": item["sha256"]}
        ram = main_ram(snapshot)
        image = Path(trial["image"])
        raw, row_size = read_rgb_png(image)
        for y in range(8, 24):
            row = raw[y * row_size + 1:(y + 1) * row_size]
            for col in range(1, 4):
                for i, expected in enumerate(expected_column(ram, y, col)):
                    x = col * 14 + i
                    actual = int.from_bytes(row[x * 3:x * 3 + 3], "big")
                    if actual != expected:
                        raise ValueError(f"{name}: pixel ({x},{y}) "
                                         f"${actual:06X} != ${expected:06X}")
                    total += 1
    assert total == len(trials) * 16 * 3 * 14
    assert report["terrain"]["tile06"]["pixel_bounds"][2] == 43
    assert report["terrain"]["tile0E"]["pixel_bounds"][2] == 43
    print(f"HGR byte/neighbor/phase palette predicts {total} retained-frame "
          "pixels across ten terrain/control trials")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AssertionError, ValueError, KeyError, TypeError) as error:
        print(f"outdoor HGR palette verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
