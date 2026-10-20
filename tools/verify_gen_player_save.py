#!/usr/bin/env python3
"""Verify GEN's successful save and byte-identical U1.VARS payload."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

from baseline import MANIFEST, describe
from disassemble import ROOT
from trace_gen_confirm_yes import status_carry
from verify_intro_support import main_ram, require


REPORT = ROOT / "build" / "traces" / "gen-player-save" / "handoff.json"
SAVE_START = 0x7E6D
SAVE_LENGTH = 0x01CA


def main() -> int:
    if not REPORT.is_file():
        print("PENDING GEN player save trace")
        return 0
    report = json.loads(REPORT.read_text())
    require(report["input"] == [
        {"key_ascii": 78, "at_pc": "0x8F9A"},
        {"key_ascii": 89, "at_pc": "0x8F12"},
    ], "player save inputs differ")
    require([p["pc"] for p in report["checkpoints"]] ==
            ["0x8F9A", "0x8EEE", "0x8F12", "0x8F23", "0x8F2C", "0x895B"],
            "player save checkpoint sequence differs")
    require(report["save_carry_set"] is False and
            not status_carry(report["checkpoints"][4]["cpu"]),
            "player save did not clear carry")
    require(" a=00 " in report["checkpoints"][4]["cpu"],
            "player save return code differs")
    for key in ("source_snapshot", "blank_player_disk", "working_player_disk", "snapshot"):
        item = report[key]
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                f"{key} differs from report")
    require(report["blank_player_disk"]["sha256"] !=
            report["working_player_disk"]["sha256"],
            "working player disk did not change")
    manifest = json.loads(MANIFEST.read_text())
    cp2 = manifest["extractor"]["path"]
    disk = Path(report["working_player_disk"]["path"])
    catalog = subprocess.run([cp2, "catalog", "--wide", str(disk)],
                             capture_output=True, text=True, check=True).stdout
    require('ProDOS "U1.PLAYER"' in catalog and
            "BIN 7e6d" in catalog and "458" in catalog and "U1.VARS" in catalog,
            "saved file catalog differs")
    with tempfile.TemporaryDirectory(dir=ROOT / "build") as tmp:
        subprocess.run([cp2, "extract", f"--exdir={tmp}", "--no-add-ext",
                        str(disk), "U1.VARS"],
                       capture_output=True, text=True, check=True)
        file_bytes = (Path(tmp) / "U1.VARS").read_bytes()
    ram = main_ram(Path(report["snapshot"]["path"]))
    require(len(file_bytes) == SAVE_LENGTH and
            file_bytes == ram[SAVE_START:SAVE_START + SAVE_LENGTH],
            "U1.VARS differs from the saved RAM range")
    require(file_bytes[0x4A] == 0 and file_bytes[0x4B:0x58] == b"A" + bytes(12),
            "saved sex/name fields differ")
    require(list(file_bytes[0x5B:0x67:2]) == [35, 35, 10, 10, 10, 15] and
            file_bytes[0x5C:0x67:2] == bytes(6),
            "saved attribute slots differ")
    require(file_bytes[0x69] == 1 and file_bytes[0x6B] == 1,
            "saved race/class fields differ")
    print("GEN player save: A=$00 carry clear; $895B continuation")
    print("U1.VARS: 458 bytes match RAM $7E6D-$8036 exactly")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"GEN player-save verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
