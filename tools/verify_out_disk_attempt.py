#!/usr/bin/env python3
"""Verify the stalled relative OUT disk read and preserve its evidence."""

import json
from pathlib import Path
import struct
import sys

from baseline import describe
from disassemble import ROOT
from trace_out_disk_attempt import drive_head_offset
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "out-disk-attempt" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING OUT disk fallback trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["checkpoints"] == [], "OUT disk fallback returned unexpectedly")
    require("OUT disk read return: no breakpoint hit; pc=D388" in report["timeout"],
            "OUT read stopped at a different point")
    require(report["final_cpu"].startswith("pc=D388 ") and
            report["final_path"] == "OUT", "final CPU or path differs")
    for key in ("source_snapshot", "working_game_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    prior = json.loads((ROOT / "build" / "traces" / "out-ram-attempt" /
                        "handoff.json").read_text())
    require(report["source_snapshot"] == prior["snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "disk attempt does not descend from RAM fallback")
    before = Path(report["source_snapshot"]["path"]).read_bytes()
    after = Path(report["snapshot"]["path"]).read_bytes()
    before_head = struct.unpack_from("<h", before, drive_head_offset(before))[0]
    after_head = struct.unpack_from("<h", after, drive_head_offset(after))[0]
    require(before_head == 38 and 0 <= after_head < 140,
            "Disk II head positions differ from trace")
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(ram[0xBA79:0xBA7D] == b"\x03OUT", "relative OUT path was lost")
    print(f"OUT relative read: no return at $16C8; paused in $D388 delay loop; "
          f"head {before_head} → {after_head} quarter-tracks")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"OUT disk-attempt verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
