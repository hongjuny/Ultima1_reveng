#!/usr/bin/env python3
"""Replay 10, 20, 21, and 100 food packs from the same shop prompt."""

import sys

from disassemble import ROOT
from trace_twn_buy_one import main as replay


if __name__ == "__main__":
    try:
        for quantity in (10, 20, 21, 100):
            output = ROOT / "build" / "traces" / f"twn-buy-{quantity}"
            if replay(quantity, output):
                raise SystemExit(1)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN multi-digit purchase failed: {error}", file=sys.stderr)
        raise SystemExit(1)
