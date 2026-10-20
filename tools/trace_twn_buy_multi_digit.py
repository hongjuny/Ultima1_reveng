#!/usr/bin/env python3
"""Replay 10, 20, and 21 food packs across the 100-Coin boundary."""

import sys

from disassemble import ROOT
from trace_twn_buy_one import main as replay


if __name__ == "__main__":
    try:
        for quantity in (10, 20, 21):
            output = ROOT / "build" / "traces" / f"twn-buy-{quantity}"
            if replay(quantity, output):
                raise SystemExit(1)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN multi-digit purchase failed: {error}", file=sys.stderr)
        raise SystemExit(1)
