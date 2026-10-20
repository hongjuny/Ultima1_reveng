#!/usr/bin/env python3
"""Continue the verified castle route two steps to a town tile."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_out_direction import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


TRACE = ROOT / "build" / "traces"
SOURCE = TRACE / "out-route-to-04" / "step-11" / "handoff.json"
OUTPUT = TRACE / "out-route-to-06"


def main() -> int:
    source = SOURCE
    for step, key, position, code in (
            (12, 0x08, (29, 31), 1),
            (13, 0x0A, (29, 32), 6)):
        target = OUTPUT / f"step-{step:02d}"
        if replay(key, source, target):
            return 1
        report = json.loads((target / "handoff.json").read_text())
        ram = main_ram(Path(report["snapshot"]["path"]))
        if cpu_pc(report["final_cpu"]) != 0x8A6C or (ram[0], ram[1]) != position or \
                report["tile_lookup"]["code"] != code:
            raise RuntimeError(f"town route step {step} differs")
        source = target / "handoff.json"
    print("town route: (30,31) → (29,31) → (29,32), tile code $06")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT town route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
