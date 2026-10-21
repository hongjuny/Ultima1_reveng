#!/usr/bin/env python3
"""Verify a completed odd quest survives death and pays a castle gem."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from trace_out_odd_castle_route import KEYS, shortest
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
DEATH1 = TRACE / "odd-quest-death-probe"
DEATH2 = TRACE / "odd-quest-death-probe-2"
ROUTE = TRACE / "odd-quest-return-castle-route"
ENTRY = TRACE / "odd-quest-reenter-castle"
KING = TRACE / "odd-quest-return-king-route"
AWARD = TRACE / "odd-quest-natural-gem-award/handoff.json"


def report(path):
    return json.loads(path.read_text())


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def follow(path, previous, disk, pc, quest=255, key=None):
    item = report(path)
    ram = checked(item["snapshot"])
    require(item["source_snapshot"] == previous["snapshot"] and
            item["working_game_disk"] == disk and
            item.get("timeout") is None and
            item["final_cpu"].startswith(f"pc={pc}") and ram[0x7EAA] == quest and
            (key is None or item["input"]["key_ascii"] == key),
            f"quest return lineage differs: {path}")
    return item, ram


def main():
    if not AWARD.is_file():
        print("PENDING natural odd quest gem award")
        return 0
    previous = report(TRACE / "odd-quest-natural-hunt/action-003/key/handoff.json")
    disk = previous["working_game_disk"]
    ram = checked(previous["snapshot"])
    require(ram[0x7EAA] == 255 and ram[0xA506] == 3,
            "completed dungeon quest source differs")
    previous, ram = follow(TRACE / "odd-quest-return/after-kill/handoff.json",
                           previous, disk, "8DDA")
    require(int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 28,
            "post-kill HP differs")
    for name, key in (("level3-step-01", 10), ("level3-step-02", 11),
                      ("level3-attack-01", 65), ("level3-attack-02", 65)):
        directory = TRACE / "odd-quest-return" / name
        action, _ = follow(directory / "key/handoff.json", previous, disk,
                           "8E0E", key=key)
        previous, ram = follow(directory / "poll/handoff.json", action, disk, "8DDA")
    require(int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 5 and
            (ram[0xB099 + 3*11 + 7] & 0xF0) == 0x10,
            "occupied stair and low HP differ")
    for directory, event, hp, pc in ((DEATH1, "dungeon_poll", [4, 0], "8DDA"),
                                      (DEATH2, "death", [250, 255], "98DD")):
        action, _ = follow(directory / "space/handoff.json", previous, disk,
                           "8E0E", key=32)
        previous, ram = follow(directory / "event/handoff.json", action, disk, pc)
        require(previous["state"]["event"] == event and
                previous["state"]["hp"] == hp and
                previous["state"]["quest"] == [0, 255, 0, 0, 0, 0, 0, 0],
                f"dungeon death event {event} differs")
    previous, ram = follow(TRACE / "odd-quest-death-selector/handoff.json",
                           previous, disk, "88FD")
    require([p["pc"] for p in previous["checkpoints"]] ==
            ["0x88F8", "0x88FD"] and
            previous["state"]["outdoor_position"] == [43, 15],
            "dungeon death selector differs")
    previous, ram = follow(TRACE / "odd-quest-resurrect-out/handoff.json",
                           previous, disk, "8A6C")
    require(previous["memory_match_at_load"] is True and
            list(ram[:2]) == [8, 47] and
            list(ram[0x7E75:0x7E79]) == [0] * 4 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 99 and
            int.from_bytes(ram[0x7EE5:0x7EE7], "little") == 99,
            "resurrected completed quest state differs")
    grid = ram[0x6000:0x7000]
    path = shortest(grid, (8, 47), (22, 20))
    record = report(ROUTE / "route.json")
    require(len(path) == len(record) == 73, "castle return route length differs")
    position = (8, 47)
    for index, destination in enumerate(path, 1):
        item = record[index - 1]
        key = KEYS[(destination[0]-position[0], destination[1]-position[1])]
        report_path = ROUTE / f"step-{index:02d}/handoff.json"
        step, ram = follow(report_path, previous, disk, "8A6C", key=key)
        require(item["number"] == index and item["before"] == list(position) and
                item["after"] == list(destination) and
                item["result_report"] == str(report_path) and
                tuple(ram[:2]) == destination and
                step["tile_lookup"]["code"] == grid[destination[1]*64+destination[0]] >> 1,
                f"castle return walk step {index} differs")
        previous, position = step, destination
    for name, pc in (("enter", "88FD"), ("load", "8956"), ("poll", "8A27")):
        previous, ram = follow(ENTRY / f"{name}/handoff.json", previous, disk, pc)
    require(list(ram[:2]) == [0, 9] and ram[0x9E3B] == 1 and
            list(ram[0x7E75:0x7E79]) == [0] * 4,
            "completed quest castle entry differs")
    path = [(x, 9) for x in range(1, 26)] + [(25, y) for y in (8, 7, 6)]
    record = report(KING / "route.json")
    require(len(record) == len(path) == 28, "king return route length differs")
    position = (0, 9)
    for index, destination in enumerate(path, 1):
        item = record[index - 1]
        key = 21 if index <= 25 else 11
        report_path = KING / f"step-{index:02d}/handoff.json"
        step, ram = follow(report_path, previous, disk, "8A27", key=key)
        require(item["number"] == index and item["before"] == list(position) and
                item["after"] == list(destination) and
                tuple(ram[:2]) == destination,
                f"king return walk step {index} differs")
        previous, position = step, destination
    award = report(AWARD)
    ram = checked(award["snapshot"])
    require(award["source_snapshot"] == previous["snapshot"] and
            award["working_game_disk"] == disk and award["input"] == 84 and
            award["initial"] ==
            {"position": [25, 6], "index": 1, "king_tile": 0x6C,
             "quest": [0, 255, 0, 0, 0, 0, 0, 0],
             "gems": [0] * 4, "group": 0} and
            [p["pc"] for p in award["checkpoints"]] ==
            ["0x92AA", "0x92CC", "0x94E7", "0x959D", "0x95BC", "0x963A", "0x963D"] and
            award["final"] == {"quest": [0] * 8, "gems": [1, 0, 0, 0],
                               "index": 1} and
            list(ram[0x7EA9:0x7EB1]) == [0] * 8 and
            list(ram[0x7E75:0x7E79]) == [1, 0, 0, 0],
            "natural red gem award differs")
    print("natural quest 1: completion survives DNG death and OUT resurrection;")
    print("73 OUT moves, 28 CAS moves, T: $7EAA $FF→0, red gem $7E75 0→1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"natural odd quest gem verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
