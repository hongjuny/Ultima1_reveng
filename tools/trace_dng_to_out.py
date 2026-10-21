#!/usr/bin/env python3
"""Follow the first dungeon K exit through OUT reload and first input."""

from disassemble import ROOT
from trace_cas_to_out import main


if __name__ == "__main__":
    raise SystemExit(main(
        ROOT / "build/traces/dng-exit-k/handoff.json",
        ROOT / "build/traces/dng-to-out", expected_coords="2b0f"))
