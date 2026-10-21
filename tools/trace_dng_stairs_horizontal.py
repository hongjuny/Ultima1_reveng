#!/usr/bin/env python3
"""Test K at the first $07 stairs while facing horizontally."""

import sys

from disassemble import ROOT
from trace_dng_after_up import main as next_poll
from trace_dng_key_w import main as press_key


SOURCE = ROOT / "build/traces/dng-descend/action-017/poll/handoff.json"
OUTPUT = ROOT / "build/traces/dng-stairs-horizontal"


def main() -> int:
    if press_key(75, OUTPUT / "key", SOURCE, probe_stair=True):
        return 1
    return next_poll(OUTPUT / "key/handoff.json", OUTPUT / "poll")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"DNG horizontal stair replay failed: {error}", file=sys.stderr)
        raise SystemExit(1)
