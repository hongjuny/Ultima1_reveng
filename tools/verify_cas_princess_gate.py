#!/usr/bin/env python3
"""Verify controlled CAS princess-exit ace and experience boundaries."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_cas_princess_gate import OUTPUT, SOURCE, TRIALS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    report_path = OUTPUT / "handoff.json"
    if not report_path.is_file():
        print("PENDING CAS princess gate runtime replay")
        return 0
    report = json.loads(report_path.read_text())
    source = json.loads(SOURCE.read_text())
    require(report["source_snapshot"] == source["snapshot"],
            "source snapshot lineage differs")
    require(report["working_game_disk"] == source["working_game_disk"],
            "working disk lineage differs")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private input changed")

    castle = (ROOT / "extracted/CAS").read_bytes()
    require(castle[0x8AC1-0x8956:0x8AC4-0x8956] == bytes.fromhex("201e84"),
            "princess narrative call differs")
    require(castle[0x8B38-0x8956] == 0xAD,
            "reward skip target is not an instruction start")
    require(castle[0x8B65-0x8956:0x8B7B-0x8956] == bytes.fromhex(
        "ad b6 7e c9 14 90 0c ad e7 7e c9 58 ad e8 7e e9 1b b0 03 4c fa 8b"),
        "qualification code differs")
    require(castle[0x8BF5-0x8956:0x8BFA-0x8956] == bytes.fromhex("a9 01 8d b5 7e"),
            "request write differs")

    require(set(report["trials"]) == set(TRIALS), "trials differ")
    for name, (ace, experience) in TRIALS.items():
        run = report["trials"][name]
        intervention = run["controlled"]
        require(intervention["edge_tile"] == {"before": 35, "after": 4} and
                intervention["narrative_skip"] == {
                    "address": "$8AC1", "before": "201e84", "after": "4c388b",
                    "target": "$8B38"} and
                intervention["ace"] == {"before": 0, "after": ace} and
                intervention["experience"] == {"before": 0, "after": experience},
                f"{name}: intervention differs")
        qualified = ace >= 20 and experience + 500 >= 7000
        expected_path = ["0x8AC1", "0x8B65", "0x8B7B" if qualified else "0x8B78"]
        if qualified:
            expected_path.append("0x8BF5")
        expected_path.append("0x8BFA")
        require([point["pc"] for point in run["checkpoints"]] == expected_path and
                run["adjusted_experience"] == experience + 500 and
                run["qualified"] == qualified and
                run["request_at_exit"] == int(qualified) and
                run["final_cpu"].startswith("pc=8BFA"),
                f"{name}: reward, qualification, or request differs")
    print("CAS princess gate: ace 19/20 and pre-reward XP 6499/6500 boundaries match")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS princess gate verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
