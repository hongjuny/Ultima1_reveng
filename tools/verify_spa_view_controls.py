#!/usr/bin/env python3
"""Check SPA nested view controls and HyperJump fuel boundary."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_spa_command_survey import OUTPUT
from trace_spa_view_controls import COMMANDS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fuel(state):
    return state["$7EE9"] + 256 * state["$7EEA"]


def main():
    path = OUTPUT / "view-controls.json"
    if not path.is_file():
        print("PENDING SPA view-control replay")
        return 0
    report = json.loads(path.read_text())
    source, disk = report["source_snapshot"], report["working_game_disk"]
    for item in (source, disk):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    stages = json.loads((OUTPUT / "stages.json").read_text())
    require(source == stages["source_snapshot"] and disk == stages["working_game_disk"],
            "SPA view route lineage changed")
    require(set(report["runs"]) == set(COMMANDS), "view control runs missing")
    for name, (key, target, start_fuel) in COMMANDS.items():
        run = report["runs"][name]
        require(run["key"] == key and run["target"] == f"${target:04X}" and
                run["start_fuel"] == start_fuel, f"{name}: command parameters changed")
        path_pcs = [point["pc"] for point in run["checkpoints"]]
        common = ["0x9298", "0x9361", "0x93B5", "0x93D8", f"0x{target:04X}"]
        suffix = (["0xA154", "0xA1BA"] if name == "h_fuel100"
                  else ["0x93DB", "0x9361"])
        require(path_pcs == common + suffix, f"{name}: execution path changed")
        initial = run["initial"]
        final = run["next_input"] or run.get("debit_exit")
        require(final is not None and run["timeout"] is None,
                f"{name}: no completed checkpoint")
        require((initial["$7EEB"], initial["$7EEC"]) ==
                (final["$7EEB"], final["$7EEC"]),
                f"{name}: shield changed")
        if name == "h_fuel100":
            require(fuel(initial) == 100 and fuel(run["debit_entry"]) == 100 and
                    fuel(final) == 0 and run["next_input"] is None and
                    " a=64 " in run["checkpoints"][-2]["cpu"],
                    "H Fuel 100 debit differs")
        else:
            require(run["final_cpu"].startswith("pc=9361") and
                    run["next_input"] is not None,
                    f"{name}: did not return to view poll")
    base = report["runs"]["space"]
    require(fuel(base["initial"]) == fuel(base["next_input"]) == 995,
            "view Space changed fuel")
    for name, address, delta in (("up", "$93FA", 0xFC),
                                 ("down", "$93FA", 4),
                                 ("right", "$93F9", 4),
                                 ("left", "$93F9", 0xFC)):
        run = report["runs"][name]
        require(fuel(run["initial"]) == 995 and fuel(run["next_input"]) == 993 and
                run["initial"][address] == 0 and
                run["next_input"][address] == delta,
                f"{name}: velocity or Fuel differs")
    h = report["runs"]["h"]
    require(fuel(h["initial"]) == 995 and fuel(h["next_input"]) == 895 and
            h["initial"]["$0000"] == 5 and h["next_input"]["$0000"] == 4,
            "H: Fuel or sector X differs")
    low = report["runs"]["h_fuel99"]
    require(fuel(low["initial"]) == fuel(low["next_input"]) == 99,
            "H Fuel 99 refusal differs")
    print("SPA view movement ±4 at cost 2; H rejects 99 and debits 100 at threshold")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SPA view-control verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
