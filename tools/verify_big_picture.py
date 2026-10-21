#!/usr/bin/env python3
"""Check private turn, overlay-loop, and memory-residency evidence."""

import json
from pathlib import Path

from disassemble import ROOT


TRACES = ROOT / "build/traces"
FILES = (TRACES / "turn-contracts/comparison.json",
         TRACES / "overlay-loop-probes/probes.json",
         TRACES / "memory-lifetime/regions.json",
         TRACES / "out-board-transitions/probe.json",
         TRACES / "tm-page1/probe.json",
         TRACES / "tm-intro-pages/probe.json",
         TRACES / "spa-first-key/probe.json",
         TRACES / "tm-first-key/probe.json")


def main():
    if any(not path.is_file() for path in FILES):
        print("PENDING big-picture runtime probes (run trace_turn_contracts.py, "
              "probe_overlay_loops.py, inspect_memory_lifetime.py)")
        return
    turns, loops, memory, boarding, page1, tm_intro, spa_key, tm_key = (
        json.loads(path.read_text()) for path in FILES)
    expected = {"OUT": ("0x8A6C", "$9357", "$7E4F"),
                "DNG": ("0x8DDA", "$8E95", "$A4E9"),
                "CAS": ("0x8A27", "$8A93", "$7EDA"),
                "TWN": ("0x8A1E", "$8A8A", "$7EDA")}
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
    assert boarding["ordinary"]["checkpoints"][-1]["pc"] == "0x8D1F"
    assert boarding["spa"]["checkpoints"][-2]["pc"] == "0x8A53"
    assert boarding["spa"]["checkpoints"][-1]["pc"] == "0x8A5F"
    assert boarding["tm"]["checkpoints"][-1]["pc"] == "0x881B"
    assert boarding["spa"]["craft_after"] == 6
    assert boarding["tm"]["craft_after"] == 10
    assert page1["checkpoints"][0]["pc"] == "0x881E"
    assert " a=20 " in page1["checkpoints"][0]["cpu"]
    assert page1["checkpoints"][1]["pc"] == "0x882A"
    assert [x["pc"] for x in tm_intro["checkpoints"] if x["label"].endswith("accepted")] == ["0x882A"] * 3
    assert [x["pc"] for x in tm_intro["checkpoints"]][-2:] == ["0x8E5E", "0x9815"]
    assert spa_key["handler"] == "$9207"
    assert spa_key["checkpoints"][-1]["pc"] == "0x8A5F"
    assert tm_key["handler"] == "$9801"
    assert tm_key["checkpoints"][-1]["pc"] == "0x9815"
    assert turns["CAS"]["after_next_poll"]["player"]["addresses"] == turns["TWN"]["after_next_poll"]["player"]["addresses"]
    assert turns["CAS"]["after_next_poll"]["zero_page"]["addresses"] == turns["TWN"]["after_next_poll"]["zero_page"]["addresses"]
    assert turns["CAS"]["after_next_poll"]["player"]["values"] == turns["TWN"]["after_next_poll"]["player"]["values"]
    assert spa_key["player"]["values"]["$7EDA"] == [0, 5]
    assert tm_key["player"]["values"]["$7EDA"] == [0, 16]
    print("six module turns, controlled B transitions, four TM intro pages, and residency verified")


if __name__ == "__main__":
    main()
