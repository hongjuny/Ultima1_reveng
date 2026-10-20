#!/usr/bin/env python3
"""Compare quantity 100 with 499, 500, and 512 Coin."""

import sys

from disassemble import ROOT
from trace_twn_buy_one import main as replay


if __name__ == "__main__":
    try:
        for coin in (499, 500, 512):
            output = ROOT / "build" / "traces" / f"twn-buy-100-coin-{coin}"
            if replay(100, output, coin_override=coin):
                raise SystemExit(1)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN high-Coin purchase failed: {error}", file=sys.stderr)
        raise SystemExit(1)
