#!/usr/bin/env python3
"""Verify controlled SPA Fire hit, reward, and twentieth-kill branch."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_spa_kill_counter import OUTPUT, SHIP_CELL, SURVEY_OUTPUT, TRIALS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    path = OUTPUT / "handoff.json"
    if not path.is_file():
        print("PENDING SPA kill-counter runtime replay")
        return 0
    report = json.loads(path.read_text())
    stages = json.loads((SURVEY_OUTPUT / "stages.json").read_text())
    require(report["source_snapshot"] == stages["source_snapshot"] and
            report["working_game_disk"] == stages["working_game_disk"],
            "SPA source lineage differs")
    for item in (report["source_snapshot"], report["working_game_disk"]):
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]},
                "private input changed")
    space = (ROOT / "extracted/SPA").read_bytes()
    require(space[0x9732-0x8956:0x9740-0x8956] == bytes.fromhex(
        "ee b6 7e d0 03 ce b6 7e ad b6 7e c9 14 90"),
        "counter and ace comparison code differs")
    require(set(report["runs"]) == set(TRIALS), "SPA Fire trials missing")
    ship = f"${SHIP_CELL:04X}"
    for name, starting_count in TRIALS.items():
        run = report["runs"][name]
        source, view, before, target = (run[k] for k in
                                        ("source", "view", "before_target", "target"))
        hit, reward, counted, result = (run[k] for k in
                                         ("hit", "reward", "counted", "result"))
        require((source["$0000"], source["$0001"], source["$7EB6"], source[ship]) ==
                (5, 5, 0, 0xC0), f"{name}: source changed")
        require((view["$0000"], view["$0001"], view["$7EB6"], view[ship]) ==
                (3, 2, starting_count, 0xC0), f"{name}: sector intervention differs")
        require(before["$9286"] == 0 and target["$9286"] == 3 and
                target[ship] == 0xC0 and
                run["aim"] == [target["$93F2"], target["$93F3"]] and
                [hit["$00BA"], hit["$00BB"]] == run["aim"],
                f"{name}: visible target or aim intervention differs")
        require(before["$7EE9"] + 256*before["$7EEA"] ==
                view["$7EE9"] + 256*view["$7EEA"] - 10,
                f"{name}: Fire fuel cost differs")
        require(hit[ship] == 0xC0 and reward[ship] == counted[ship] == 0x80 and
                reward["$7EE7"] == counted["$7EE7"] == 100 and
                reward["$7EE8"] == counted["$7EE8"] == 0 and
                hit["$7EB6"] == reward["$7EB6"] == starting_count and
                counted["$7EB6"] == result["$7EB6"] == starting_count + 1,
                f"{name}: hit reward or ship count differs")
        expected = ["0x9361", "0x964D", "0x9675", "0x967D",
                    "0x9700", "0x9732", "0x973A",
                    "0x9766" if starting_count == 19 else "0x9763"]
        require([p["pc"] for p in run["checkpoints"]] == expected and
                run["final_cpu"].startswith(f"pc={expected[-1][2:]}"),
                f"{name}: execution path differs")
    print("SPA Fire: existing ship C0→80, +100 XP, count 0→1 and 19→20 ace branch")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"SPA kill-counter verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
