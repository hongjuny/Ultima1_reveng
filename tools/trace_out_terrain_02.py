#!/usr/bin/env python3
"""Step from ($27,$22) onto the neighboring raw-$04 terrain tile."""

from pathlib import Path
import sys

from disassemble import ROOT
from trace_out_direction import main as replay


if __name__ == "__main__":
    try:
        raise SystemExit(replay(
            0x0A,
            ROOT / "build" / "traces" / "out-direction-0a" / "handoff.json",
            ROOT / "build" / "traces" / "out-terrain-02",
        ))
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT terrain-02 trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
