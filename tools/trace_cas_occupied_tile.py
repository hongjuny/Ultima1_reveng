#!/usr/bin/env python3
"""Approach the castle actor at (1,6) and test its occupied tile."""

from pathlib import Path
import sys

from disassemble import ROOT
from trace_cas_step_right import main as trace_direction


TRACE = ROOT / "build" / "traces"
OUTPUT = TRACE / "cas-occupied-tile"
SOURCE = TRACE / "cas-step-right" / "handoff.json"


def main() -> int:
    source = SOURCE
    for number in (1, 2, 3):
        output = OUTPUT / f"step-{number:02d}"
        result = trace_direction(0x0B, source, output)
        if result:
            return result
        source = output / "handoff.json"
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"CAS occupied-tile trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
