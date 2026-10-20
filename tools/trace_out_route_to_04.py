#!/usr/bin/env python3
"""Walk a live-map route from the first outdoor poll onto a code-$04 tile."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_out_direction import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


TRACE = ROOT / "build" / "traces"
OUTPUT = TRACE / "out-route-to-04"
KEYS = (0x0B, 0x0B) + (0x08,) * 9


def main() -> int:
    source = TRACE / "out-first-input" / "handoff.json"
    for number, key in enumerate(KEYS, 1):
        target = OUTPUT / f"step-{number:02d}"
        print(f"\n[route step {number}/{len(KEYS)} key ${key:02X}]", flush=True)
        if replay(key, source, target):
            return 1
        report = json.loads((target / "handoff.json").read_text())
        if cpu_pc(report["final_cpu"]) != 0x8A6C:
            raise RuntimeError(f"route step {number} left the outdoor input loop")
        ram = main_ram(Path(report["snapshot"]["path"]))
        expected = (39 - max(0, number - 2), 33 - min(2, number))
        actual = (ram[0], ram[1])
        if actual != expected:
            raise RuntimeError(f"route step {number}: expected {expected}, got {actual}")
        expected_tile = 4 if number == len(KEYS) else 1
        if report["tile_lookup"]["code"] != expected_tile:
            raise RuntimeError(f"route step {number} tile differs from map")
        source = target / "handoff.json"
    print(f"route completed at {actual}: code ${expected_tile:02X}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT route trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
