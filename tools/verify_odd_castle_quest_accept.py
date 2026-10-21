#!/usr/bin/env python3
"""Verify ordinary outdoor and castle inputs leading to odd quest acceptance."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
OUT = TRACE / "out-odd-castle-route"
ENTRY = TRACE / "odd-castle-entry"
KING = TRACE / "odd-castle-king-route"
ACCEPT = TRACE / "odd-castle-quest-accept/handoff.json"


def report(path):
    return json.loads(path.read_text())


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def main():
    if not ACCEPT.is_file():
        print("PENDING natural odd castle quest acceptance")
        return 0
    source = report(TRACE / "out-first-input/handoff.json")
    disk = source["working_game_disk"]
    route = report(OUT / "route.json")
    require(len(route) == 38, "outdoor route length differs")
    position = (39, 33)
    for index, item in enumerate(route, 1):
        path = OUT / f"step-{index:02d}/handoff.json"
        step = report(path)
        ram = checked(step["snapshot"])
        actual = tuple(ram[:2])
        delta = (actual[0] - position[0], actual[1] - position[1])
        require(item["number"] == index and item["source_report"] ==
                (str(TRACE / "out-first-input/handoff.json") if index == 1 else
                 str(OUT / f"step-{index-1:02d}/handoff.json")) and
                item["result_report"] == str(path) and
                item["before"] == list(position) and item["after"] == list(actual) and
                step["source_snapshot"] == source["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                delta in ((0, -1), (0, 1), (1, 0), (-1, 0)) and
                step["input"]["key_ascii"] == {(0, -1): 11, (0, 1): 10,
                                                   (1, 0): 21, (-1, 0): 8}[delta] and
                item["tile_code"] == step["tile_lookup"]["code"],
                f"outdoor step {index} differs")
        source, position = step, actual
    require(position == (22, 20), "second castle coordinate differs")
    for stage, path, pc in (("enter", ENTRY / "enter/handoff.json", "pc=88FD"),
                            ("load", ENTRY / "load/handoff.json", "pc=8956"),
                            ("poll", ENTRY / "poll/handoff.json", "pc=8A27")):
        step = report(path)
        ram = checked(step["snapshot"])
        require(step["source_snapshot"] == source["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                step["final_cpu"].startswith(pc), f"castle {stage} lineage differs")
        if stage == "enter":
            require(step["input"]["key_ascii"] == 69, "castle E input differs")
        source = step
    require(ram[0x9E3B] == 1 and ram[0x7EED] == 1 and
            list(ram[:2]) == [0, 9] and list(ram[0x7EA9:0x7EB1]) == [0] * 8,
            "second castle initial state differs")
    route = report(KING / "route.json")
    require(len(route) == 28, "king route length differs")
    position = (0, 9)
    for index, item in enumerate(route, 1):
        path = KING / f"step-{index:02d}/handoff.json"
        step = report(path)
        ram = checked(step["snapshot"])
        actual = tuple(ram[:2])
        delta = (actual[0] - position[0], actual[1] - position[1])
        require(item["number"] == index and item["before"] == list(position) and
                item["after"] == list(actual) and item["source_report"] ==
                (str(ENTRY / "poll/handoff.json") if index == 1 else
                 str(KING / f"step-{index-1:02d}/handoff.json")) and
                item["result_report"] == str(path) and
                step["source_snapshot"] == source["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                step["final_cpu"].startswith("pc=8A27") and
                delta == ((1, 0) if index <= 25 else (0, -1)) and
                step["input"]["key_ascii"] == (21 if index <= 25 else 11) and
                ram[0x9E3B] == 1 and ram[0x7EAA] == 0,
                f"king approach step {index} differs")
        source, position = step, actual
    require(position == (25, 6) and ram[0xB400 + 6 * 38 + 25] == 0x6C,
            "king tile differs")
    trial = report(ACCEPT)
    after = checked(trial["snapshot"])
    require(trial["source_snapshot"] == source["snapshot"] and
            trial["working_game_disk"] == disk and trial["before"] ==
            {"position": [25, 6], "quest": [0] * 8, "world_location": 1,
             "group": 0, "castle_index": 1, "king_tile": 0x6C} and
            trial["inputs"] == [84, 83] and
            trial["after_quest"] == [0, 1, 0, 0, 0, 0, 0, 0] and
            list(after[0x7EA9:0x7EB1]) == trial["after_quest"] and
            [point["pc"] for point in trial["checkpoints"]] ==
            ["0x927C", "0x92AA", "0x92CC", "0x8A25", "0x93FB", "0x9437", "0x943A"],
            "ordinary odd quest acceptance differs")
    print("38 OUT moves, E, 28 CAS moves, T/S: quest 1 $7EAA 0→1 without RAM edits")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd castle quest verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
