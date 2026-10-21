#!/usr/bin/env python3
"""Verify packed NIF rows are consumed without the inherited 512-byte tail."""

import hashlib
import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_tm_nif_render import OUTPUT, SOURCE


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING TM packed NIF render trace")
        return 0
    report = json.loads(path.read_text())
    prior = json.loads(SOURCE.read_text())
    require((report["source_snapshot"], report["working_game_disk"]) ==
            (prior["snapshot"], prior["working_game_disk"]),
            "NIF render source ancestry changed")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    require([point["pc"] for point in report["points"]] ==
            ["0x90AA", "0x90E7", "0x90FE", "0x90E7", "0x9108", "0x9132"],
            "NIF animation checkpoints changed")
    require(report["first_source"] == "$6000" and
            report["first_target"] == "$5FD0" and
            report["second_source"] == "$6028" and
            report["first_matches_nif"] and
            report["first_target_changed"] and
            report["first_target_matches"],
            "first NIF row copy differs")
    require(report["consumed_source"] == "$7E00" and
            report["consumed_count"] == 0 and
            report["final_source"] == "$6000" and
            report["final_cpu"].startswith("pc=9132"),
            "192-row completion or final reset differs")
    require(report["final_pages"]["page1"] ==
            {"matching_bytes": 7680, "matching_rows": 192},
            "final HGR page 1 does not exactly match packed NIF")
    nif = (ROOT / "extracted/NIF").read_bytes()
    require(len(nif) == 7680 and
            report["nif_sha256"] == hashlib.sha256(nif).hexdigest(),
            "NIF source bytes changed")
    print("TM NIF: 192 packed 40-byte rows consumed $6000–$7DFF; "
          "final HGR page 1 matches all 7680 payload bytes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"TM NIF render verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
