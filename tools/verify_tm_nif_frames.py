#!/usr/bin/env python3
"""Verify sampled NIF scroll frames against private source and HGR pages."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_tm_nif_frames import OUTPUT, SAMPLE_ROWS, SOURCE


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING TM NIF intermediate frame trace")
        return 0
    report = json.loads(path.read_text())
    prior = json.loads(SOURCE.read_text())
    require((report["source_snapshot"], report["working_game_disk"]) ==
            (prior["snapshot"], prior["working_game_disk"]),
            "NIF frame source ancestry changed")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    nif = (ROOT / "extracted/NIF").read_bytes()
    require(len(nif) == 7680 and
            report["nif_sha256"] == hashlib.sha256(nif).hexdigest(),
            "NIF source bytes changed")
    require(report["row_copy_hits"] == 192 and
            report["sample_rows"] == sorted(SAMPLE_ROWS) and
            len(report["samples"]) == len(SAMPLE_ROWS) and
            report["final_cpu"].startswith("pc=9101"),
            "NIF frame sample coverage changed")
    cycles = report["row_copy_cycles"]
    require(len(cycles) == 192 and all(isinstance(item, int) for item in cycles),
            "NIF row cycle capture incomplete")
    intervals = [b - a for a, b in zip(cycles, cycles[1:])]
    require(intervals[0] == 116977 and
            min(intervals[1:]) == 119167 and
            max(intervals[1:]) == 119254 and
            cycles[-1] - cycles[0] == 22766880,
            "NIF animation cycle profile differs")
    for sample, consumed in zip(report["samples"], sorted(SAMPLE_ROWS)):
        target = "$4000" if consumed & 1 else "$2000"
        address = "$5FD0" if consumed & 1 else "$3FD0"
        require(sample["consumed"] == consumed and
                sample["cpu"].startswith("pc=90FE") and
                sample["remaining_before_decrement"] == 193 - consumed and
                sample["next_source"] == f"${0x6000 + 40 * consumed:04X}" and
                sample["last_destination"] == address and
                sample["matching_lower_rows"][target] == consumed and
                sample["video_switches"] == {"TEXT": 0, "MIXED": 0,
                                             "PAGE2": 0 if consumed & 1 else 1,
                                             "HIRES": 1} and
                sample["after_flip_cpu"].startswith("pc=9101") and
                sample["video_after_flip"] == {"TEXT": 0, "MIXED": 0,
                                               "PAGE2": 1 if consumed & 1 else 0,
                                               "HIRES": 1},
                f"NIF row {consumed} frame or page differs")
    print("TM NIF frames: nine sampled row counts across 192 copies; "
          "alternating HGR writes precede the video page flip; "
          "steady row intervals 119167–119254 CPU cycles")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF frame verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
