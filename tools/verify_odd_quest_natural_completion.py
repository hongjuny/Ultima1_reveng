#!/usr/bin/env python3
"""Verify the unmodified-input quest path from dungeon entry to completion."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
DESCENT = TRACE / "odd-quest-descend"
SPAWN = TRACE / "odd-quest-spawn-search"
HUNT = TRACE / "odd-quest-natural-hunt"


def report(path):
    return json.loads(path.read_text())


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private snapshot changed: {path}")
    return main_ram(path)


def step(path, previous, disk, pc, quest=1, key=None):
    item = report(path)
    ram = checked(item["snapshot"])
    require(item["source_snapshot"] == previous["snapshot"] and
            item["working_game_disk"] == disk and item["timeout"] is None and
            item["final_cpu"].startswith(f"pc={pc}") and ram[0x7EAA] == quest and
            (key is None or item["input"]["key_ascii"] == key),
            f"ordinary action lineage or quest differs: {path}")
    return item, ram


def main():
    final_path = HUNT / "action-003/key/handoff.json"
    if not final_path.is_file():
        print("PENDING natural odd quest third-floor completion")
        return 0
    previous = report(TRACE / "odd-quest-dng-entry/poll/handoff.json")
    disk = previous["working_game_disk"]
    ram = checked(previous["snapshot"])
    require(ram[0x7EAA] == 1 and ram[0xA506] == 1,
            "accepted first-floor source differs")
    for depth, count in ((1, 17), (2, 24)):
        directory = DESCENT / f"level-{depth}"
        actions = report(directory / "route.json")
        require(len(actions) == count, f"floor {depth} route length differs")
        for index, action in enumerate(actions, 1):
            key_path = directory / f"action-{index:03d}/key/handoff.json"
            poll_path = directory / f"action-{index:03d}/poll/handoff.json"
            require(action["number"] == index and
                    action["source_report"] ==
                    (str(TRACE / "odd-quest-dng-entry/poll/handoff.json")
                     if depth == 1 and index == 1 else
                     str(DESCENT / "level-1/descent/handoff.json")
                     if depth == 2 and index == 1 else
                     str(directory / f"action-{index-1:03d}/poll/handoff.json")) and
                    action["result_report"] == str(poll_path),
                    f"floor {depth} action {index} route differs")
            key_item, _ = step(key_path, previous, disk, "8E0E", key=action["key"])
            previous, ram = step(poll_path, key_item, disk, "8DDA")
            require(ram[0xA506] == depth and
                    list(ram[0xA4E8:0xA4EA]) == action["after"] and
                    int.from_bytes(ram[0x7EC6:0x7EC8], "little") == action["hp_after"],
                    f"floor {depth} action {index} state differs")
        turn = directory / "stairs-turn"
        key = report(turn / "key/handoff.json")["input"]["key_ascii"]
        turn_key, _ = step(turn / "key/handoff.json", previous, disk, "8E0E", key=key)
        previous, ram = step(turn / "poll/handoff.json", turn_key, disk, "8DDA")
        require(report(directory / "stairs-source.json")["source_report"] ==
                str(turn / "poll/handoff.json") and
                ram[0xB099 + 11 * ram[0xA4E9] + ram[0xA4E8]] == 7,
                f"floor {depth} descending stair differs")
        previous, ram = step(directory / "descent/handoff.json", previous, disk,
                             "8DDA", key=75)
        require(ram[0xA506] == depth + 1, f"floor {depth} descent differs")
    search = report(SPAWN / "search.json")
    selected = report(SPAWN / "selected.json")
    require(len(search) == 3 and selected == search[2] and
            search[0]["source_report"] ==
            str(DESCENT / "level-2/stairs-turn/poll/handoff.json") and
            not search[0]["slot5"]["active"] and
            not search[1]["slot5"]["active"] and
            search[2]["slot5"] == {"active": True, "position": [6, 1], "hp": 45},
            "bounded ordinary spawn selection differs")
    # The selected branch starts at the same pre-descent stair poll, then
    # advances two Space turns before taking K. The other K trials are probes.
    previous = report(DESCENT / "level-2/stairs-turn/poll/handoff.json")
    for waits in (1, 2):
        directory = SPAWN / f"wait-{waits:02d}/space"
        key_item, _ = step(directory / "key/handoff.json", previous, disk,
                           "8E0E", key=32)
        previous, ram = step(directory / "poll/handoff.json", key_item, disk, "8DDA")
        require(ram[0xA506] == 2, f"stair wait {waits} depth differs")
    require(selected["source_report"] ==
            str(SPAWN / "wait-02/space/poll/handoff.json"),
            "selected branch did not follow both Space turns")
    previous, ram = step(Path(selected["result_report"]), previous, disk,
                         "8DDA", key=75)
    require(ram[0xA506] == 3 and ram[0xA50D] == 0 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 28,
            "selected type-five spawn differs")
    hunt = report(HUNT / "route.json")
    require([a["key"] for a in hunt] == [11, 65, 65] and
            [a["quest_after"] for a in hunt] == [1, 1, 255],
            "natural hunt keys or quest outcomes differ")
    for index, action in enumerate(hunt, 1):
        directory = HUNT / f"action-{index:03d}"
        key_item, ram = step(directory / "key/handoff.json", previous, disk,
                             "8E0E", quest=255 if index == 3 else 1,
                             key=action["key"])
        require(action["source_report"] ==
                (selected["result_report"] if index == 1 else
                 str(HUNT / f"action-{index-1:03d}/poll/handoff.json")) and
                action["result_report"] ==
                str(directory / ("key/handoff.json" if index == 3 else "poll/handoff.json")),
                f"hunt action {index} ancestry differs")
        if index < 3:
            previous, ram = step(directory / "poll/handoff.json", key_item, disk,
                                 "8DDA")
        else:
            previous = key_item
    require(ram[0x7EAA] == 255 and ram[0xA506] == 3 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 28 and
            hunt[2]["completed"] is True,
            "natural odd quest completion differs")
    print("natural CAS acceptance → DNG depth 3 → slot-5 kill: $7EAA 0→1→$FF")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"natural odd quest verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
