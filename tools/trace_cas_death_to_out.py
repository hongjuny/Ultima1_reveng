#!/usr/bin/env python3
"""Follow the controlled castle death through the OUT overlay reload."""

from disassemble import ROOT
from trace_cas_to_out import main as trace_out


if __name__ == "__main__":
    raise SystemExit(trace_out(
        ROOT / "build" / "traces" / "cas-guard-death" / "handoff.json",
        ROOT / "build" / "traces" / "cas-death-to-out", death_path=True))
