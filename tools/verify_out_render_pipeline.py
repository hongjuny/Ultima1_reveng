#!/usr/bin/env python3
"""Verify the private outdoor text-to-video trace and its ancestry."""

import json
from pathlib import Path
import re
import sys

from baseline import describe
from disassemble import ROOT


SOURCE = ROOT / "build" / "traces" / "out-space-effect" / "handoff.json"
REPORT = ROOT / "build" / "traces" / "out-render-pipeline" / "handoff.json"
EXPECTED_PCS = (0x8995, 0x8119, 0x8062, 0x15B0, 0x1A1D, 0x8065,
                0x89A1, 0x836E, 0x8A6C)
EXPECTED_VIDEO = tuple(
    f"${address:04X}" for address in
    (0x27D0, 0x2BD0, 0x2FD0, 0x33D0, 0x37D0, 0x3BD0,
     0x47D0, 0x4BD0, 0x4FD0, 0x53D0, 0x57D0, 0x5BD0)
)


def check_file(item: dict) -> None:
    path = Path(item["path"])
    assert describe(path) == {"size": item["size"], "sha256": item["sha256"]}


def main() -> int:
    if not REPORT.is_file():
        print("PENDING outdoor render trace; run tools/trace_out_render_pipeline.py")
        return 0
    source = json.loads(SOURCE.read_text())
    report = json.loads(REPORT.read_text())
    assert report["source_snapshot"] == source["snapshot"]
    assert report["working_game_disk"] == source["working_game_disk"]
    check_file(report["source_snapshot"])
    check_file(report["working_game_disk"])
    check_file(report["snapshot"])
    assert tuple(int(item["pc"], 16) for item in report["checkpoints"]) == EXPECTED_PCS
    cycles = [int(re.search(r"\bcycles=(\d+)", item["cpu"]).group(1))
              for item in report["checkpoints"]]
    assert cycles == sorted(cycles) and len(set(cycles)) == len(cycles)
    assert re.search(r"\ba=0E\b", report["character_cpu"])
    assert report["changed_video_addresses"] == list(EXPECTED_VIDEO)
    assert report["video_before_sha256"] != report["video_after_sha256"]
    assert report["frame_before"]["sha256"] == report["frame_after"]["sha256"]
    assert report["frame_before"]["frame"] == report["frame_after"]["frame"]
    assert report["frame_next_poll"]["frame"] > report["frame_after"]["frame"]
    assert report["frame_next_poll"]["sha256"] != report["frame_after"]["sha256"]
    assert re.search(r"\bpc=8A6C\b", report["final_cpu"])
    print("OUT inline text → STUPH glyph → 12 graphics-page byte changes; "
          "next frame pixels differ")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AssertionError, KeyError, ValueError, AttributeError) as error:
        print(f"OUT render pipeline verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
