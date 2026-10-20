#!/usr/bin/env python3
"""Replay all four outdoor direction keys from the same private snapshot."""

import sys

from trace_out_direction import DIRECTION_KEYS, main as replay


if __name__ == "__main__":
    try:
        for key in DIRECTION_KEYS:
            print(f"\n[direction ${key:02X}]", flush=True)
            if replay(key):
                raise SystemExit(1)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"OUT direction batch failed: {error}", file=sys.stderr)
        raise SystemExit(1)
