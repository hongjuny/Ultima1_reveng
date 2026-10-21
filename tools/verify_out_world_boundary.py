#!/usr/bin/env python3
"""Check the controlled OUT world transition and saved world bits."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_out_world_boundary import OUTPUT


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING controlled OUT world-boundary replay")
        return 0
    report = json.loads(path.read_text())
    prior = json.loads((ROOT / "build/traces/out-first-input/handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "OUT source lineage changed")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private input changed")
    require(report["key"] == 11 and
            [point["pc"] for point in report["points"]] ==
            ["0x8A74", "0x9416", "0x9477", "0x9496", "0x94C1",
             "0x9503", "0x952C", "0x8A6C"],
            "OUT world boundary execution path changed")
    before, intervened = report["before_intervention"], report["intervened"]
    require({key: value for key, value in intervened.items() if value != before[key]} ==
            {"$000C": 0x4A} and before["$000C"] == 39,
            "controlled intervention was not only pending X")
    require((before["$7E6F"], before["$7E70"]) == (0, 0) and
            (report["masked"]["$0000"], report["masked"]["$7E6F"]) == (0xF6, 1) and
            report["encoded_before"]["$7E70"] == 0 and
            (report["encoded"]["$7E6F"], report["encoded"]["$7E70"]) == (1, 0x40),
            "world index or encoded bits differ")
    require(report["final"]["$7E6F"] == 1 and
            report["final"]["$7E70"] == 0x40 and
            report["final"]["$0000"] == 0xF6 and
            report["final_cpu"].startswith("pc=8A6C") and
            report["map_initial_sha256"] != report["map_after_sha256"],
            "world map was not changed at next OUT poll")
    print("OUT east boundary: segment 0→1, X=$F6, object world bits=$40, map changed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT world-boundary verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
