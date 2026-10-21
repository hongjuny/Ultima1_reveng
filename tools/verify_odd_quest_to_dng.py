#!/usr/bin/env python3
"""Verify that an accepted odd quest survives castle exit and dungeon entry."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_out_route_to_07 import route
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
AFTER = TRACE / "odd-castle-after-quest/handoff.json"
EXIT = TRACE / "odd-castle-exit-route"
RETURN = TRACE / "odd-castle-return-out"
WALK = TRACE / "odd-quest-route-to-dng"
ENTRY = TRACE / "odd-quest-dng-entry"


def report(path):
    return json.loads(path.read_text())


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def quest(ram):
    return list(ram[0x7EA9:0x7EB1])


def main():
    if not (ENTRY / "poll/handoff.json").is_file():
        print("PENDING natural odd quest carried to DNG")
        return 0
    accepted = report(TRACE / "odd-castle-quest-accept/handoff.json")
    disk = accepted["working_game_disk"]
    previous = accepted
    continued = report(AFTER)
    ram = checked(continued["snapshot"])
    require(continued["source_snapshot"] == previous["snapshot"] and
            continued["working_game_disk"] == disk and
            continued["input"] == {"key_ascii": 32, "at_pc": "0x160D"} and
            [p["pc"] for p in continued["checkpoints"]] == ["0x160D", "0x8A27"] and
            list(ram[:2]) == [25, 6] and quest(ram) == [0, 1, 0, 0, 0, 0, 0, 0],
            "king message continuation differs")
    previous = continued
    steps = report(EXIT / "route.json")
    require(len(steps) == 28, "castle return route length differs")
    position = (25, 6)
    for index, item in enumerate(steps, 1):
        path = EXIT / f"step-{index:02d}/handoff.json"
        step = report(path)
        ram = checked(step["snapshot"])
        actual = tuple(ram[:2])
        expected = (25, 6 + index) if index <= 3 else (28 - index, 9)
        require(item["number"] == index and item["before"] == list(position) and
                item["after"] == list(actual) and item["result_report"] == str(path) and
                step["source_snapshot"] == previous["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                step["input"]["key_ascii"] == (10 if index <= 3 else 8) and
                step["final_cpu"].startswith("pc=8A27") and actual == expected and
                quest(ram) == [0, 1, 0, 0, 0, 0, 0, 0],
                f"castle return step {index} differs")
        previous, position = step, actual
    for name, pc in (("leave", "pc=88FD"), ("load", "pc=8A6C")):
        path = RETURN / f"{name}/handoff.json"
        step = report(path)
        ram = checked(step["snapshot"])
        require(step["source_snapshot"] == previous["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                step["final_cpu"].startswith(pc) and
                quest(ram) == [0, 1, 0, 0, 0, 0, 0, 0],
                f"castle OUT {name} differs")
        previous = step
    require(list(ram[:2]) == [22, 20] and
            report(RETURN / "load/handoff.json")["memory_match_at_load"] is True,
            "second castle outdoor return differs")
    expected_route = route(ram, (22, 20))
    path_record = report(WALK / "route.json")
    require(len(expected_route) == path_record["steps"] == 26 and
            expected_route[-1][1:] == ((43, 15), 7) and
            path_record["source"] == str(RETURN / "load/handoff.json"),
            "dungeon approach route differs")
    for index, (key, position, code) in enumerate(expected_route, 1):
        path = WALK / f"step-{index:02d}/handoff.json"
        step = report(path)
        ram = checked(step["snapshot"])
        require(step["source_snapshot"] == previous["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                step["final_cpu"].startswith("pc=8A6C") and
                step["input"]["key_ascii"] == key and tuple(ram[:2]) == position and
                step["tile_lookup"]["code"] == code and
                quest(ram) == [0, 1, 0, 0, 0, 0, 0, 0],
                f"dungeon approach step {index} differs")
        previous = step
    for name, pc in (("enter", "pc=88FD"), ("load", "pc=8956"),
                     ("poll", "pc=8DDA")):
        path = ENTRY / f"{name}/handoff.json"
        step = report(path)
        ram = checked(step["snapshot"])
        require(step["source_snapshot"] == previous["snapshot"] and
                step["working_game_disk"] == disk and step["timeout"] is None and
                step["final_cpu"].startswith(pc) and
                quest(ram) == [0, 1, 0, 0, 0, 0, 0, 0],
                f"DNG {name} differs")
        previous = step
    require(report(ENTRY / "load/handoff.json")["memory_match"] is True and
            list(ram[:2]) == [43, 15] and ram[0xA506] == 1 and
            list(ram[0xA4E8:0xA4EA]) == [1, 1],
            "accepted quest DNG first input differs")
    print("T/S quest 1 survives 28 CAS moves, OUT reload, 26 OUT moves, and DNG entry")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest to DNG verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
