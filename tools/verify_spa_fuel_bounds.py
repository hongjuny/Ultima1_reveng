#!/usr/bin/env python3
"""Check controlled SPA Up behavior at Fuel 0, 4, and 5."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_spa_fuel_bounds import FUELS, OUTPUT
from trace_spa_direction_controls import SOURCE


def require(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING SPA Fuel boundary runtime replay")
        return 0
    report = json.loads(path.read_text())
    source = json.loads(SOURCE.read_text())["spa"]["snapshot"]
    require(report["source_snapshot"] == source, "source lineage differs")
    for item in (source, report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private input changed")
    require(set(report["runs"]) == {str(fuel) for fuel in FUELS},
            "Fuel trials missing")
    for fuel in FUELS:
        run = report["runs"][str(fuel)]
        original, changed, final = (run[k] for k in
                                    ("original", "intervened", "final"))
        require(original["$7EE9"] + 256*original["$7EEA"] == 1000 and
                changed["$7EE9"] + 256*changed["$7EEA"] == fuel and
                all(original[k] == changed[k] for k in original
                    if k not in ("$7EE9", "$7EEA")),
                f"Fuel {fuel}: intervention differs")
        points = [p["pc"] for p in run["points"]]
        expected = (["0x8A5F"] if fuel == 0 else
                    ["0x8FAD", "0xA154", "0xA1BA", "0x8A5F"])
        require(points == expected and run["final_cpu"].startswith("pc=8A5F"),
                f"Fuel {fuel}: execution path differs")
        require(final["$7EE9"] == final["$7EEA"] == 0 and
                final["$7EEB"] + 256*final["$7EEC"] == 1000 and
                final["$928A"] == (0 if fuel == 0 else 0xFE) and
                final["$928B"] == 0,
                f"Fuel {fuel}: result differs")
        if fuel:
            require(run["service_entry"]["$7EE9"] == fuel and
                    run["service_exit"]["$7EE9"] == 0 and
                    " a=05 " in run["points"][1]["cpu"],
                    f"Fuel {fuel}: five-unit debit differs")
    print("SPA Up: Fuel 0 refuses dispatch; Fuel 4/5 moves and saturates at 0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SPA Fuel boundary verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
