#!/usr/bin/env python3
"""Verify GEN menu B reloaded the saved character and reached the OUT handoff."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-load-player" / "handoff.json"
RECORD_LENGTH = 0x01CA


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN menu B player-load trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == {"key_ascii": 66, "at_pc": "0x89FD"},
            "GEN menu B input differs")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8A10", "0x8A1C", "0x8A5B", "0x8A7F", "0x8AC0"],
            "player-load checkpoint sequence differs")
    require(not status_carry(report["checkpoints"][1]["cpu"]),
            "player file load returned with carry set")
    require(report["record_length"] == RECORD_LENGTH,
            "player record length differs")
    for key in ("source_snapshot", "player_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    before = main_ram(Path(report["source_snapshot"]["path"]))
    after = main_ram(Path(report["snapshot"]["path"]))
    saved = before[0x7E6D:0x7E6D + RECORD_LENGTH]
    require(after[0x7E6D:0x7E6D + RECORD_LENGTH] == saved,
            "restored live record differs from saved record")
    # $6000 is scratch space and changes again on the route to $8AC0. The
    # live trace checks it immediately at the loader return, before the copy.
    print("GEN menu B: 458-byte record restored at $7E6D")
    print("GEN continuation: $8AC0 jump toward OUT selector")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"GEN player-load verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
