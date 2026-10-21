#!/usr/bin/env python3
"""Compare the first Swift address transcription with SPA hit runtime states."""

import csv
import json
import os
from pathlib import Path
import subprocess
import sys

from disassemble import ROOT
from trace_spa_kill_counter import OUTPUT as TRACE_OUTPUT, SHIP_CELL, TRIALS


BUILD = ROOT / "build/port-prototype"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def probe(executable, ship, experience, count, y):
    result = subprocess.run([str(executable), str(ship), str(experience),
                             str(count), str(y)], capture_output=True,
                            text=True, check=True)
    parts = result.stdout.strip().split()
    require(len(parts) == 8, f"unexpected Swift result: {result.stdout}")
    return (int(parts[0]), int(parts[1]), int(parts[2]), parts[3],
            int(parts[4]), tuple(int(flag) for flag in parts[5:]))


def main():
    instruction_file = ROOT / "build/ghidra-project/SPA-instructions.tsv"
    with instruction_file.open(newline="") as source:
        instructions = {int(row["address"], 16): row
                        for row in csv.DictReader(source, delimiter="\t")}
    for address, mnemonic in ((0x9700, "LDA"), (0x9732, "INC"),
                              (0x973A, "LDA")):
        require(instructions[address]["mnemonic"] == mnemonic,
                f"Ghidra did not recover SPA ${address:04X}")
    BUILD.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CLANG_MODULE_CACHE_PATH"] = str(BUILD / "clang-cache")
    env["SWIFT_MODULE_CACHE_PATH"] = str(BUILD / "swift-cache")
    executable = BUILD / "space-hit-probe"
    subprocess.run(["swiftc", "port-prototype/SpaceHit.swift",
                    "port-prototype/SpaceHitProbe.swift", "-o", str(executable)],
                   cwd=ROOT, env=env, check=True)

    path = TRACE_OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING SPA hit runtime comparison; Swift probe compiled")
        return 0
    report = json.loads(path.read_text())
    require(set(report["runs"]) == set(TRIALS), "SPA runtime trials missing")
    ship_key = f"${SHIP_CELL:04X}"
    for name, starting_count in TRIALS.items():
        run = report["runs"][name]
        hit, counted = run["hit"], run["counted"]
        before_experience = hit["$7EE7"] + 256*hit["$7EE8"]
        expected_branch = "exactlyTwenty" if starting_count == 19 else "belowTwenty"
        expected_flags = (int(starting_count == 19), int(starting_count == 19),
                          int(starting_count == 0))
        expected = (counted[ship_key],
                    counted["$7EE7"] + 256*counted["$7EE8"],
                    counted["$7EB6"], expected_branch,
                    counted["$7EB6"], expected_flags)
        actual = probe(executable, hit[ship_key], before_experience,
                       hit["$7EB6"], 25)
        require(actual == expected, f"{name}: Swift {actual} != emulator {expected}")
    # Boundary cases cover arithmetic not exercised in the saved hit state.
    require(probe(executable, 0x40, 9999, 255, 25) ==
            (0, 9999, 255, "aboveTwenty", 255, (1, 0, 1)),
            "experience or count saturation differs")
    print("Swift SPA $9700-$9741 matches two emulator hit states and saturation cases")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Swift space-hit verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
