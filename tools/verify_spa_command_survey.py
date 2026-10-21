#!/usr/bin/env python3
"""Check distinct SPA command dispatch and private replay provenance."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_spa_command_survey import COMMANDS, OUTPUT
from trace_spa_long_commands import CONTINUE, STAGES
from verify_intro_support import main_ram


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING SPA distinct-command runtime survey")
        return 0
    report = json.loads(path.read_text())
    source = report["source_snapshot"]
    disk = report["working_game_disk"]
    for item in (source, disk):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private source changed")
    expected = json.loads((ROOT / "build/traces/out-board-transitions/probe.json").read_text())["spa"]["snapshot"]
    require(source == expected, "SPA snapshot lineage changed")
    ram = main_ram(Path(source["path"]))
    require((ram[0x923F], ram[0x9240], ram[0x928A], ram[0x928B],
             ram[0x7EE9], ram[0x7EEA]) == (3, 0, 0, 0, 0xE8, 0x03),
            "initial SPA heading, coordinates or fuel changed")
    require(set(report["runs"]) == set(COMMANDS), "command runs missing")
    for name, (key, target) in COMMANDS.items():
        run = report["runs"][name]
        require(run["key"] == key and run["target"] == f"${target:04X}",
                f"{name}: key or target changed")
        require([point["pc"] for point in run["checkpoints"][:3]] ==
                ["0x8A62", "0x8AB0", f"0x{target:04X}"],
                f"{name}: actual handler path changed")
        if name in ("ctrl_a", "h", "n"):
            require(run["boundary"] == "0x8A5F" and run["timeout"] is None and
                    run["final_cpu"].startswith("pc=8A5F"),
                    f"{name}: expected completed next input")
        else:
            require(run["boundary"] is None and run["timeout"] and
                    run["final_cpu"].startswith("pc=160D"),
                    f"{name}: expected bounded, unresolved replay")
    require(report["runs"]["v"]["after"]["spa"]["values"].get("$928A") == [0, 0xFE],
            "V: observed local movement changed")
    require(report["runs"]["v"]["after"]["player"]["values"].get("$7EE9") == [0xE8, 0xE3],
            "V: observed five-unit fuel debit changed")
    stages_path = OUTPUT / "stages.json"
    require(stages_path.is_file(), "SPA internal-stage trace missing")
    stages = json.loads(stages_path.read_text())
    require(stages["source_snapshot"] == source and stages["working_game_disk"] == disk,
            "SPA internal-stage lineage changed")
    require(set(stages["runs"]) == set(STAGES), "SPA internal stages missing")
    for name, (key, addresses) in STAGES.items():
        run = stages["runs"][name]
        expected_path = (["0x8A62"] + [f"0x{address:04X}" for address in addresses] +
                         ([f"0x{CONTINUE[name][1]:04X}"] if name in CONTINUE else []) +
                         ({"i": ["0x90D8"],
                           "v": ["0x93D8", "0x95BF"]}.get(name, [])))
        require(run["key"] == key and
                [point["pc"] for point in run["checkpoints"]] == expected_path,
                f"{name}: internal stage path changed")
    require(stages["runs"]["v"]["subcommand_target"] == "$95BF",
            "V Space: patched subcommand target changed")
    print("SPA six distinct command targets verified; I/V/Z remain bounded observations")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SPA command survey verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
