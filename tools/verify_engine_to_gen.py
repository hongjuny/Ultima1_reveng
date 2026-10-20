#!/usr/bin/env python3
"""Check the private first-overlay snapshot and its resident memory map."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "engine-to-gen" / "handoff.json"


def main() -> int:
    if not REPORT.is_file():
        print("PENDING engine-to-GEN trace")
        return 0
    report = json.loads(REPORT.read_text())
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8975", "0xB703", "0x897E", "0x88FD", "0x8907",
             "0xB703", "0x890E", "0x8956"], "first module checkpoint sequence differs")
    for index in (2, 6):
        cpu = report["checkpoints"][index]["cpu"]
        require((int(cpu.split(" p=")[1][:2], 16) & 1) == 0,
                f"loader at checkpoint {index} returned with carry set")
    require("a=00" in report["checkpoints"][3]["cpu"],
            "first module selector value differs")
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "GEN entry snapshot differs from report")
    ram = main_ram(path)
    engine = (ROOT / "extracted" / "MI.U1").read_bytes()
    stuph = (ROOT / "extracted" / "STUPH").read_bytes()
    gen = (ROOT / "extracted" / "GEN").read_bytes()
    require(ram[0x7000:0x8954] == engine[:0x1954],
            "resident MI.U1 range $7000–$8953 differs")
    require(ram[0x8956:0x8956 + len(gen)] == gen,
            "GEN overlay differs from extraction at entry")
    changed = [0x0800 + i for i, (a, b) in enumerate(zip(ram[0x0800:0x2000], stuph))
               if a != b]
    require(changed == [0x172A, 0x172D, 0x175C],
            f"unexpected STUPH changes at GEN entry: {[hex(a) for a in changed[:16]]}")
    print("MI.U1 resident $7000–$8953 matches; GEN overlay 8932 bytes match at $8956")
    print("STUPH resident $0800–$1FFF; changed bytes $172A, $172D, $175C")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"engine-to-GEN verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
