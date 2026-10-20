#!/usr/bin/env python3
"""Walk from first town input to the code-$66 food-shop tile."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_twn_direction import main as replay
from trace_startup import cpu_pc
from verify_intro_support import main_ram


TRACE = ROOT / "build" / "traces"
SOURCE = TRACE / "twn-first-input" / "handoff.json"
OUTPUT = TRACE / "twn-to-food-shop"
KEYS = (0x0B,) * 6 + (0x15,) * 4


def main() -> int:
    source = SOURCE
    for step, key in enumerate(KEYS, 1):
        target = OUTPUT / f"step-{step:02d}"
        print(f"[town route {step}/{len(KEYS)} key ${key:02X}]", flush=True)
        if replay(key, source, target):
            return 1
        report = json.loads((target / "handoff.json").read_text())
        position = (19, 17 - step) if step <= 6 else (19 + step - 6, 11)
        ram = main_ram(Path(report["snapshot"]["path"]))
        if cpu_pc(report["final_cpu"]) != 0x8A1E or \
                tuple(report["position_after"]) != position or \
                tuple(ram[0:2]) != position:
            raise RuntimeError(f"town route step {step}: expected {position}")
        source = target / "handoff.json"
    tile = ram[0xB400 + 11 * 38 + 23]
    if tile != 0x66:
        raise RuntimeError(f"food-shop tile differs: ${tile:02X}")
    print("town food-shop route reached (23,11), tile $66")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN food-shop route failed: {error}", file=sys.stderr)
        raise SystemExit(1)
