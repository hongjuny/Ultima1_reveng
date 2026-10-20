#!/usr/bin/env python3
"""Inject Space at the first outdoor input and inspect its command dispatch."""

import sys

from disassemble import ROOT
from trace_out_key_p import run


if __name__ == "__main__":
    try:
        raise SystemExit(run(32, ROOT / "build" / "traces" / "out-key-space"))
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT key-Space trace failed: {error}", file=sys.stderr)
        raise SystemExit(1)
