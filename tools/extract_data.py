#!/usr/bin/env python3
"""Extract verified data records from user-supplied game files locally."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
TCMAPS_BASE = 0x4000
TCMAPS_SIZE = 7660
TCMAPS_COUNT = 10
TCMAPS_HEADER_SIZE = 2 * TCMAPS_COUNT
TCMAPS_RECORD_SIZE = 764
TCMAPS_RUNTIME_COPY_SIZE = 3 * 256


def extract_tcmaps(check_only: bool) -> int:
    source = ROOT / "extracted" / "TCMAPS"
    if not source.is_file():
        print(f"missing {source}", file=sys.stderr)
        return 2
    data = source.read_bytes()
    if len(data) != TCMAPS_SIZE:
        print(f"TCMAPS length mismatch: {len(data)} != {TCMAPS_SIZE}", file=sys.stderr)
        return 1
    pointers = struct.unpack(f"<{TCMAPS_COUNT}H", data[:TCMAPS_HEADER_SIZE])
    expected = tuple(
        TCMAPS_BASE + TCMAPS_HEADER_SIZE + i * TCMAPS_RECORD_SIZE
        for i in range(TCMAPS_COUNT)
    )
    if pointers != expected:
        print("TCMAPS pointer table does not match ten contiguous 764-byte records", file=sys.stderr)
        return 1
    output = ROOT / "build" / "data" / "TCMAPS"
    records = []
    chunks = []
    for index, address in enumerate(pointers):
        offset = address - TCMAPS_BASE
        chunk = data[offset:offset + TCMAPS_RECORD_SIZE]
        if len(chunk) != TCMAPS_RECORD_SIZE:
            print(f"TCMAPS record {index} truncated", file=sys.stderr)
            return 1
        chunks.append(chunk)
        filename = f"record_{index:02d}.bin"
        available = min(TCMAPS_RUNTIME_COPY_SIZE, len(data) - offset)
        records.append({
            "index": index,
            "address": f"0x{address:04X}",
            "offset": offset,
            "size": len(chunk),
            "runtime_copy_bytes_available_in_file": available,
            "sha256": hashlib.sha256(chunk).hexdigest(),
            "file": filename,
        })
        if not check_only:
            output.mkdir(parents=True, exist_ok=True)
            (output / filename).write_bytes(chunk)
        print(f"record {index:02d}: ${address:04X}-${address+len(chunk)-1:04X} ({len(chunk)} bytes)")
        if available < TCMAPS_RUNTIME_COPY_SIZE:
            print(f"  runtime copy extends {TCMAPS_RUNTIME_COPY_SIZE-available} bytes past the file payload")
    if b"".join(chunks) != data[TCMAPS_HEADER_SIZE:]:
        print("TCMAPS records do not cover the payload exactly", file=sys.stderr)
        return 1
    if not check_only:
        if b"".join((output / r["file"]).read_bytes() for r in records) != data[TCMAPS_HEADER_SIZE:]:
            print("written TCMAPS records do not reconstruct the packed payload", file=sys.stderr)
            return 1
        manifest = {
            "source": "TCMAPS",
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "load_address": f"0x{TCMAPS_BASE:04X}",
            "pointer_table_size": TCMAPS_HEADER_SIZE,
            "slot_stride": TCMAPS_RECORD_SIZE,
            "runtime_copy_size": TCMAPS_RUNTIME_COPY_SIZE,
            "runtime_copy_destination": "0xB400",
            "records": records,
        }
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"wrote {output.relative_to(ROOT)} (local game data; ignored by Git)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate and print record ranges only")
    args = parser.parse_args()
    return extract_tcmaps(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
