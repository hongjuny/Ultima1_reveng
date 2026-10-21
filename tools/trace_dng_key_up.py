#!/usr/bin/env python3
"""Replay Up at the first DNG poll."""

import sys
from disassemble import ROOT
from trace_dng_key_w import main

if __name__ == "__main__":
    try:
        raise SystemExit(main(0x0B, ROOT / "build/traces/dng-key-up"))
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG Up trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
