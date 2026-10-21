#!/usr/bin/env python3
"""Compare controlled final-craft spawn with the same ordinary CAS → OUT return."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
CONTROL = TRACE / "final-craft-spawn/handoff.json"


def checked(report):
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not CONTROL.is_file():
        print("PENDING controlled final craft spawn")
        return 0
    source = json.loads((TRACE / "cas-exit-left/handoff.json").read_text())
    baseline = json.loads((TRACE / "cas-to-out/handoff.json").read_text())
    trial = json.loads(CONTROL.read_text())
    require(trial["source_snapshot"] == source["snapshot"] ==
            baseline["source_snapshot"] and
            trial["working_game_disk"] == baseline["working_game_disk"],
            "craft replay ancestry differs")
    prior, ordinary, spawned = checked(source), checked(baseline), checked(trial)
    require(trial["intervention"] ==
            {"address": "0x7EB5", "before": 0, "after": 1} and
            prior[0x7EB5] == 0 and trial["initial"]["request"] == 0 and
            trial["initial"]["object_count"] == 0 and
            trial["initial"]["limit"] < 7,
            "craft request intervention differs")
    require([point["pc"] for point in trial["checkpoints"]] ==
            ["0x8956", "0x9567", "0x958C", "0x9927", "0x9591", "0x9596", "0x8A6C"],
            "craft producer path differs")
    item = trial["placement"]
    address = item["address"]
    require((item["x"], item["y"], address) == (6, 7, 0x61C6) and
            (item["raw_before"], item["raw_after"], item["raw_at_poll"]) ==
            (4, 0x1E, 0x1E) and item["request_after"] == 0 and
            item["objects_after"] == 1,
            "craft map write or reset differs")
    require([(0x6000 + index, left, right)
             for index, (left, right) in enumerate(zip(ordinary[0x6000:0x7000],
                                                       spawned[0x6000:0x7000]))
             if left != right] == [(address, 4, 0x1E)],
            "craft replay changed an unexpected world-map cell")
    require(ordinary[0x7EF6] == 0 and spawned[0x7EF6] == 1 and
            spawned[0x7F97] == 0x1E and spawned[0x7F47] == 7 and
            spawned[0x7EF7] == 6 and spawned[0x7FE7] == 4 and
            spawned[0x7EB5] == 0,
            "craft object record or one-shot request differs")
    print("Controlled CAS → OUT request created one raw $1E tile at (6,7)")
    print("Only that map cell differs from ordinary return; object record saved raw $04")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"final craft verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
