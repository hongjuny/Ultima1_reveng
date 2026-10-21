#!/usr/bin/env python3
"""Probe the three remaining HP-loss turns on the second-floor route."""

from disassemble import ROOT
from trace_dng_level2_heavy_hit import main as trace_turn


def main() -> int:
    for index in (1, 3, 9):
        source = ROOT / f"build/traces/dng-level2-to3/action-{index:03d}/key/handoff.json"
        output = ROOT / f"build/traces/dng-level2-loss-{index:03d}"
        print(f"action {index}", flush=True)
        if trace_turn(source, output):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
