#!/usr/bin/env python3
"""Check controlled speaker-access cycle intervals for STUPH IDs 0E and 10."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_spa_direction_controls import SOURCE
from trace_stuph_sound_pulses import EFFECTS, OUTPUT


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING controlled STUPH speaker timing")
        return 0
    report = json.loads(path.read_text())
    source = json.loads(SOURCE.read_text())["spa"]["snapshot"]
    require(report["source_snapshot"] == source, "source snapshot lineage differs")
    for item in (source, report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    expected_intervals = {"0E": 6441, "10": 1666}
    require(set(report["runs"]) == set(EFFECTS), "effect trials missing")
    for name, (entry, count) in EFFECTS.items():
        run = report["runs"][name]
        hits = run["hits"]
        require(run["entry"] == f"${entry:04X}" and run["injected_pc"] is True and
                run["source_cpu"].startswith("pc=8A5F") and
                run["speaker_accesses"] == count and len(hits) == count+1 and
                [hit["pc"] for hit in hits] == ["$1B3A"]*count + ["$1B41"],
                f"{name}: entry or toggle sequence differs")
        intervals = [b["cycles"]-a["cycles"] for a,b in zip(hits,hits[1:])]
        require(run["intervals"] == intervals and
                intervals == [expected_intervals[name]]*(count-1) + [12],
                f"{name}: cycle interval differs")
    print("STUPH $0E: 16 accesses / 6441-cycle intervals; "
          "$10: 50 accesses / 1666-cycle intervals")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"STUPH speaker timing verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
