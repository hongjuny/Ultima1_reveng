#!/usr/bin/env python3
"""Buy six and seven food packs to cross the 8-bit food boundary."""

import sys

from disassemble import ROOT
from trace_twn_buy_one import main as replay


if __name__ == "__main__":
    try:
        for quantity in (6, 7):
            output = ROOT / "build" / "traces" / f"twn-buy-{quantity}"
            if replay(quantity, output):
                raise SystemExit(1)
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN food carry replay failed: {error}", file=sys.stderr)
        raise SystemExit(1)
