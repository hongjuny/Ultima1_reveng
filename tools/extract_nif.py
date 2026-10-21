#!/usr/bin/env python3
"""Decode private NIF bytes as 192 packed Apple II HGR scanlines."""

import argparse
import json
from pathlib import Path
import struct
import sys
import zlib

from disassemble import ROOT


SOURCE = ROOT / "extracted/NIF"
OUTPUT = ROOT / "build/data/nif-monochrome.png"
REPORT = ROOT / "build/data/nif-format.json"
WIDTH, HEIGHT, BYTES_PER_ROW = 280, 192, 40


def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def decode(data):
    if len(data) != HEIGHT * BYTES_PER_ROW:
        raise ValueError("NIF is not 192 packed 40-byte rows")
    rows = []
    for row in range(HEIGHT):
        segment = data[row * BYTES_PER_ROW:(row + 1) * BYTES_PER_ROW]
        rows.append(bytes(255 if value & (1 << bit) else 0
                          for value in segment for bit in range(7)))
    return rows


def png(rows):
    if len(rows) != HEIGHT or any(len(row) != WIDTH for row in rows):
        raise ValueError("NIF pixel dimensions differ")
    pixels = b"".join(b"\x00" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 0, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate format without writing private image")
    args = parser.parse_args()
    data = SOURCE.read_bytes()
    rows = decode(data)
    high_bits = sum(bool(value & 0x80) for value in data)
    lit_pixels = sum(pixel != 0 for row in rows for pixel in row)
    info = {"width": WIDTH, "height": HEIGHT, "bytes_per_row": BYTES_PER_ROW,
            "payload_bytes": len(data), "high_bit_set_bytes": high_bits,
            "lit_monochrome_pixels": lit_pixels,
            "pixel_order": "seven low bits per byte, least significant bit first",
            "row_order": "file row zero first; animation inserts each row at HGR bottom"}
    if not args.check:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(png(rows))
        REPORT.write_text(json.dumps(info, indent=2) + "\n")
        print("private image:", OUTPUT)
    print(f"NIF {WIDTH}×{HEIGHT}, {high_bits}/{len(data)} phase bits set, "
          f"{lit_pixels} monochrome pixels")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        print(f"NIF extraction failed: {error}", file=sys.stderr)
        raise SystemExit(1)
