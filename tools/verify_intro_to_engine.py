#!/usr/bin/env python3
"""Check the private intro-to-engine handoff against the extracted image."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "intro-to-engine" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING intro-to-engine trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["inputs"][0]["key_ascii"] == 65, "unexpected intro key")
    points = report["checkpoints"]
    require([point["pc"] for point in points] ==
            ["0x0B23", "0x0B50", "0xB70C", "0x7000", "0x8956"],
            "intro-to-engine checkpoint sequence differs")
    require("a=C1" in points[1]["cpu"], "intro key code differs")
    require(points[3]["file_bytes_match_at_entry"] is True,
            "MI.U1 did not match at entry")
    for name in ("prekey_snapshot", "engine_snapshot"):
        item = report[name]
        path = Path(item["path"])
        require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
                f"{name} differs from report")
    ram = main_ram(Path(report["engine_snapshot"]["path"]))
    engine = (ROOT / "extracted" / "MI.U1").read_bytes()
    require(ram[0x7000:0x7000 + len(engine)] == engine,
            "MI.U1 RAM image differs from extraction")
    require(ram[0x0800:0x0800 + 16] ==
            (ROOT / "extracted" / "U1.INTRO").read_bytes()[:16],
            "intro was overwritten before the STUPH request")
    print("intro key $C1: $0B23 → $0B50 → $B70C → MI.U1 $7000 → $8956")
    print(f"MI.U1: all {len(engine)} bytes match at engine entry; intro still resident")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"intro-to-engine verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
