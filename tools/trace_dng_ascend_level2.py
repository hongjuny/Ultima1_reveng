#!/usr/bin/env python3
"""Press K at the generated level-two entrance and return to level one."""

import sys

from disassemble import ROOT
from trace_dng_stairs_k import main as replay_k


SOURCE = ROOT / "build/traces/dng-stairs-k/handoff.json"
OUTPUT = ROOT / "build/traces/dng-level2-ascend"


if __name__ == "__main__":
    try:
        raise SystemExit(replay_k(SOURCE, OUTPUT, expected_tile="08",
                                  expected_depth="02", branch="ascend"))
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG level-two ascent failed: {error}", file=sys.stderr)
        raise SystemExit(1)
