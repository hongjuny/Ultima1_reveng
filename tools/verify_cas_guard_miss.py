#!/usr/bin/env python3
"""Verify a controlled one-byte RNG change selects the guard miss branch."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_cas_guard_miss import next_random
from verify_intro_support import main_ram, require


TRACE = ROOT / "build" / "traces"
REPORT = TRACE / "cas-guard-miss" / "handoff.json"


def checked_ram(item: dict) -> bytearray:
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            "controlled guard snapshot differs")
    return main_ram(path)


def main() -> int:
    if not REPORT.is_file():
        print("PENDING CAS controlled guard miss")
        return 0
    prior = json.loads((TRACE / "cas-attack-effect" / "handoff.json").read_text())
    original = json.loads((TRACE / "cas-guard-retaliation" / "handoff.json").read_text())
    report = json.loads(REPORT.read_text())
    require(report["timeout"] is None and
            report["source_snapshot"] == prior["handler_return_snapshot"] ==
            original["source_snapshot"] and
            report["working_game_disk"] == prior["working_game_disk"],
            "guard miss source ancestry differs")
    change = report["controlled_change"]
    require(change == {"address": "0x1E27", "before": 0xA6, "after": 0x59,
                       "original_roll": 0x9D, "predicted_roll": 0x02,
                       "threshold": 0x45},
            "controlled RNG change differs")
    state = bytes(report["rng_state_before"])
    require(len(state) == 16 and state[15] == change["before"] and
            next_random(state) == change["original_roll"] and
            next_random(state[:15] + bytes((change["after"],))) ==
            change["predicted_roll"],
            "RNG state does not predict both rolls")
    snapshots = report["intervention_snapshots"]
    before = checked_ram(snapshots["before"])
    changed = checked_ram(snapshots["after"])
    require(before[0x1E18:0x1E28] == state and
            [(address, before[address], changed[address])
             for address in range(0x10000) if before[address] != changed[address]] ==
            [(0x1E27, 0xA6, 0x59)],
            "intervention changed more than the RNG seed byte")
    points = report["checkpoints"]
    require([point["pc"] for point in points] ==
            ["0x997A", "0x9981", "0x8A27"] and
            " a=02 " in points[1]["cpu"] and
            report["final_cpu"] == points[-1]["cpu"],
            "controlled guard miss path differs")
    after = checked_ram(report["snapshot"])
    require((before[0x7EC6], before[0x7EC7],
             after[0x7EC6], after[0x7EC7]) == (0x96, 0, 0x96, 0) and
            before[0xB6DE] == after[0xB6DE] == 0xDA and
            before[0xB6EE] == after[0xB6EE] == 1 and
            after[0:2] == bytes((1, 7)) and
            (after[0x7EE4], after[0x7EDA]) == (0x42, 0x30),
            "guard miss changed watched game state")
    print("CAS controlled guard miss: seed $A6→$59, roll $9D→$02 < $45")
    print("only RNG seed byte changed; player HP $0096 and actor HP $01DA stable")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"CAS guard miss verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
