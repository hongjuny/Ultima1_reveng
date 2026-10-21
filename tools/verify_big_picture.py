#!/usr/bin/env python3
"""Check private turn, overlay-loop, and memory-residency evidence."""

import json
from pathlib import Path

from disassemble import ROOT


TRACES = ROOT / "build/traces"
FILES = (TRACES / "turn-contracts/comparison.json",
         TRACES / "overlay-loop-probes/probes.json",
         TRACES / "memory-lifetime/regions.json")


def main():
    if any(not path.is_file() for path in FILES):
        print("PENDING big-picture runtime probes (run trace_turn_contracts.py, "
              "probe_overlay_loops.py, inspect_memory_lifetime.py)")
        return
    turns, loops, memory = (json.loads(path.read_text()) for path in FILES)
    expected = {"OUT": ("0x8A6C", "$9357", "$7E4F"),
                "DNG": ("0x8DDA", "$8E95", "$A4E9")}
    for name, (poll, handler, state_addr) in expected.items():
        trace = turns[name]
        assert trace["handler"] == handler
        assert trace["checkpoints"][-1]["pc"] == poll
        assert state_addr in (trace["after_next_poll"]["player"]["addresses"]
                              + trace["after_next_poll"]["dungeon"]["addresses"])
        assert trace["after_next_poll"]["video"]["count"] > 0
        assert trace["initial_frame"]["sha256"] != trace["after_next_poll"]["frame"]["sha256"]
    assert loops["SPA"]["checkpoints"][-1]["pc"] == "0x8A5F"
    assert loops["SPA"]["method"].find("bypass entry") == -1
    assert loops["TM"]["checkpoints"][-1]["pc"] == "0x9815"
    assert "bypass entry" in loops["TM"]["method"]
    for name in ("OUT", "CAS", "TWN", "DNG"):
        item = memory[name]
        assert item["overlay"]["length"] == len((ROOT / "extracted" / name).read_bytes())
        assert item["overlay"]["matching_bytes"] > item["overlay"]["length"] - 40
        assert item["engine"]["matching_bytes"] > 6300
    assert memory["CAS"]["regions_sha256"]["$6000-$6FFF"] == memory["TWN"]["regions_sha256"]["$6000-$6FFF"]
    print("OUT/DNG Up turns, SPA loop, controlled TM input, and four residency snapshots verified")


if __name__ == "__main__":
    main()
