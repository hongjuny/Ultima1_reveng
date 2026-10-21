#!/usr/bin/env python3
"""Verify the private first outdoor draw trace against its source snapshot."""

import json
from pathlib import Path
import re
import sys

from baseline import describe
from disassemble import ROOT


SOURCE = ROOT / "build/traces/out-first-input/handoff.json"
REPORT = ROOT / "build/traces/stuph-outdoor-draw/handoff.json"


def check_file(item):
    assert describe(Path(item["path"])) == {"size": item["size"],
                                             "sha256": item["sha256"]}


def main():
    if not REPORT.is_file():
        print("PENDING outdoor draw trace; run tools/run_runtime.py trace_stuph_outdoor_draw.py")
        return 0
    prior = json.loads(SOURCE.read_text())
    report = json.loads(REPORT.read_text())
    assert report["source_snapshot"] == prior["snapshot"]
    assert report["working_game_disk"] == prior["working_game_disk"]
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        check_file(report[key])
    assert report["entry"]["pc"] == "0x1C39"
    assert report["return"]["pc"] == "0x1DA6"
    assert report["return"]["cpu"] == report["final_cpu"]
    cycles = [int(re.search(r"\bcycles=(\d+)", report[key]["cpu"]).group(1))
              for key in ("entry", "return")]
    assert cycles[1] - cycles[0] == 130917
    memory = report["memory"]
    assert memory["world_map"]["changed_count"] == 0
    assert memory["row_tables"]["changed_count"] == 0
    assert memory["tile_patterns"]["changed_count"] == 14
    assert memory["video"]["changed_count"] == 5362
    assert memory["zero_page"]["changed_count"] == 42
    assert memory["support_state"]["changed_count"] == 4
    assert report["frame_after"]["number"] > report["frame_before"]["number"]
    assert report["frame_after"]["sha256"] != report["frame_before"]["sha256"]
    assert {change["address"] for change in memory["tile_patterns"]["first_changes"]} >= {
        "$0CD8", "$0D38", "$0CD9", "$0D39"}
    print("STUPH outdoor draw: 130917 cycles, 5362 video bytes and "
          "14 tile-pattern bytes changed; world map preserved")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AssertionError, ValueError, KeyError, AttributeError) as error:
        print(f"STUPH outdoor draw verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
