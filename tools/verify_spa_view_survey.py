#!/usr/bin/env python3
"""Check nested SPA command dispatch evidence and source ancestry."""

import json
from pathlib import Path
import sys

from baseline import describe
from trace_spa_command_survey import OUTPUT
from trace_spa_view_survey import COMMANDS


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    path = OUTPUT / "view-survey.json"
    if not path.is_file():
        print("PENDING SPA nested view survey")
        return 0
    report = json.loads(path.read_text())
    stages = json.loads((OUTPUT / "stages.json").read_text())
    require((report["source_snapshot"], report["working_game_disk"]) ==
            (stages["source_snapshot"], stages["working_game_disk"]),
            "SPA view source ancestry changed")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    require(set(report["runs"]) == set(COMMANDS), "view survey cases missing")
    for name, (key, target) in COMMANDS.items():
        run = report["runs"][name]
        require((run["key"], run["target"]) == (key, f"${target:04X}"),
                f"{name}: command mapping changed")
        require([point["pc"] for point in run["points"][:5]] ==
                ["0x9298", "0x9361", "0x93B5", "0x93D8", f"0x{target:04X}"],
                f"{name}: dispatch path changed")
        require(len(run["points"]) == (6 if run["boundary"] else 5) and
                (run["boundary"] is None or
                 run["boundary"] in ("0x93DB", "0x9361", "0x8A5F", "0x88FB")),
                f"{name}: boundary record malformed")
        print(f"SPA V {name}: target ${target:04X}, next {run['boundary'] or 'unresolved'}")
    expected_boundaries = {"default_a": "0x93DB", "f": "0x93DB",
                           "i": None, "r": "0x93DB", "v": "0x8A5F",
                           "z": None, "ctrl_a": "0x93DB", "n": "0x93DB"}
    for name, boundary in expected_boundaries.items():
        require(report["runs"][name]["boundary"] == boundary,
                f"{name}: observed boundary changed")
    f = report["runs"]["f"]["after"]["player"]["values"]
    require(f.get("$7EE9") == [227, 217], "F Fuel-10 effect changed")
    v = report["runs"]["v"]["after"]["player"]["values"]
    require(v.get("$7E51") == [222, 25] and
            v.get("$7E52") == [147, 146], "nested V return vector changed")
    for name, address in (("ctrl_a", "$7E71"), ("n", "$7E72")):
        values = report["runs"][name]["after"]["player"]["values"]
        require(values.get(address) == [255, 0],
                f"{name}: common-engine state change differs")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SPA view survey verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
