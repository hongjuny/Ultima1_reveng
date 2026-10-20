#!/usr/bin/env python3
"""Verify MAKE.INDATA's observed memory relocation in a private a2m snapshot."""

import json
from pathlib import Path
import struct
import sys

from baseline import describe
from disassemble import ROOT


REPORT = ROOT / "build" / "traces" / "intro-support" / "handoff.json"


def main_ram(snapshot: Path) -> bytes:
    data = snapshot.read_bytes()
    if len(data) < 32 or data[:4] != b"TS2A":
        raise ValueError("not an a2m v2 snapshot")
    offset = 32
    while offset + 8 <= len(data):
        tag = data[offset:offset + 4]
        length = struct.unpack_from("<I", data, offset + 4)[0]
        offset += 8
        if offset + length > len(data):
            raise ValueError("truncated snapshot chunk")
        if tag == b"RAM_":
            if length < 8:
                raise ValueError("short RAM chunk")
            main_size, lc_size = struct.unpack_from("<II", data, offset)
            if main_size != 131072 or lc_size != 32768 or length != 8 + main_size + lc_size:
                raise ValueError("unexpected a2m RAM layout")
            return data[offset + 8:offset + 8 + 65536]
        offset += length
    raise ValueError("snapshot has no RAM chunk")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    if not REPORT.is_file():
        print("PENDING intro support trace")
        return 0
    report = json.loads(REPORT.read_text())
    snapshot = report["snapshot"]
    path = Path(snapshot["path"])
    require(describe(path) == {"size": snapshot["size"], "sha256": snapshot["sha256"]},
            "intro support snapshot differs from trace")
    points = report["checkpoints"]
    require([item["pc"] for item in points] == ["0xB70C", "0x0F37", "0x0F41"],
            "intro support checkpoints differ")
    require(points[1]["carry_set"] is False, "MAKE.INDATA loader did not succeed")

    ram = main_ram(path)
    source = (ROOT / "extracted" / "MAKE.INDATA").read_bytes()
    require(ram[0x1E00:0x2000] == source[:512], "first MAKE.INDATA block differs")
    require(ram[0x8700:0x8F00] == source[0x200:0xA00],
            "copy from $2000–$27FF to $8700–$8EFF differs")
    require(ram[0x6000:0x8600] == source[0x9BD:0x2FBD],
            "copy from $27BD–$4DBC to $6000–$85FF differs")
    require(ram[0x2000] != source[0x200], "original $2000 load range was not reused")
    require(ram[0xBAF2:0xBAF4] == bytes((0x00, 0x1E)),
            "loader execution pointer does not target $1E00")
    require(ram[0xB70C:0xB70F] == bytes((0x4C, 0xD8, 0xB7))
            and ram[0xB7FA:0xB7FD] == bytes((0x20, 0x01, 0xB8))
            and ram[0xB801:0xB804] == bytes((0x6C, 0xF2, 0xBA)),
            "loader entry-to-execution path differs")
    print("MAKE.INDATA: first 512 bytes resident at $1E00–$1FFF")
    print("MAKE.INDATA: 2048 bytes copied $2000–$27FF → $8700–$8EFF")
    print("MAKE.INDATA: 9728 bytes copied $27BD–$4DBC → $6000–$85FF")
    print("MAKE.INDATA: loader indirect entry $1E00; original $2000 range reused")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"intro support verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
