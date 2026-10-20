#!/usr/bin/env python3
"""Replay two castle down keys, ending at the wall below the entrance."""

from pathlib import Path
import sys

from disassemble import ROOT
from trace_cas_step_right import SOURCE, main as trace_direction


OUTPUT = ROOT / "build" / "traces" / "cas-blocked-down"


def main() -> int:
    source = SOURCE
    for number in (1, 2):
        output = OUTPUT / f"step-{number:02d}"
        result = trace_direction(0x0A, source, output)
        if result:
            return result
        source = output / "handoff.json"
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        print(f"CAS blocked-down trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
