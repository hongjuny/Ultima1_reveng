#!/usr/bin/env python3
"""Check a slot-3 map move against intermediate writes and another replay."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-east-to-03-step-1/handoff.json"
MOVE = TRACE / "dng-actor-move/handoff.json"
ALTERNATE = TRACE / "dng-east-to-03-after-1/handoff.json"


def checked_ram(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG actor-move snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, MOVE, ALTERNATE)):
        print("PENDING DNG actor-move trace")
        return 0
    source, move, alternate = [json.loads(path.read_text()) for path in
                               (SOURCE, MOVE, ALTERNATE)]
    require(all(item["timeout"] is None for item in (source, move, alternate)) and
            move["source_snapshot"] == alternate["source_snapshot"] == source["snapshot"] and
            move["working_game_disk"] == alternate["working_game_disk"] ==
            source["working_game_disk"], "DNG actor-move ancestry differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG actor-move game disk differs")
    before, after = checked_ram(source["snapshot"]), checked_ram(move["snapshot"])
    require(after == checked_ram(alternate["snapshot"]),
            "DNG actor-move replay differs from independent next poll")
    checks = move["checkpoints"]
    require([item["pc"] for item in checks] ==
            ["0x98EC", "0x997F", "0x9982", "0x9985", "0x998E",
             "0x999D", "0x99A7", "0x9A01", "0x8DDA"],
            "DNG actor-move checkpoints differ")
    require([item["slot"] for item in checks[1:8]] == ["03"] * 7 and
            [(item["actor_x"], item["actor_y"],
              item["old_cell_4_3"], item["new_cell_3_3"])
             for item in checks[1:8]] ==
            [("04", "03", "33", "00"),
             ("04", "03", "33", "00"),
             ("04", "03", "03", "00"),
             ("03", "03", "03", "00"),
             ("03", "03", "03", "00"),
             ("03", "03", "03", "00"),
             ("03", "03", "03", "30")],
            "DNG actor-move intermediate writes differ")
    require(" a=03 " in checks[2]["cpu"] and
            " a=30 " in checks[6]["cpu"] and
            before[0xA511] == after[0xA511] + 1 == 4 and
            before[0xA517] == after[0xA517] == 3 and
            before[0xB099 + 3 * 11 + 4] == 0x33 and
            after[0xB099 + 3 * 11 + 4] == 0x03 and
            before[0xB099 + 3 * 11 + 3] == 0 and
            after[0xB099 + 3 * 11 + 3] == 0x30,
            "DNG actor-move nibble or coordinate state differs")
    print("DNG slot 3: (4,3) $33→$03; X 4→3; (3,3) $00→$30")
    print("Intermediate stores and full RAM match the independent next poll")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG actor-move verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
