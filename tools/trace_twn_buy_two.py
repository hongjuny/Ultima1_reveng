#!/usr/bin/env python3
"""Replay a two-pack food purchase from the same shop input snapshot."""

from pathlib import Path
import sys

from disassemble import ROOT
from trace_twn_buy_one import main


if __name__ == "__main__":
    try:
        raise SystemExit(main(2, ROOT / "build" / "traces" / "twn-buy-two"))
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"TWN buy two failed: {error}", file=sys.stderr)
        raise SystemExit(1)
