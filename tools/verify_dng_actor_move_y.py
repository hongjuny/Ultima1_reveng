#!/usr/bin/env python3
"""Check the ordinary vertical actor move and its independent replay."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_dng_actor_move import checked_ram
from verify_intro_support import require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-east-to-03-step-2/handoff.json"
MOVE = TRACE / "dng-actor-move-y/handoff.json"
ALTERNATE = TRACE / "dng-east-to-03-after-2/handoff.json"


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, MOVE, ALTERNATE)):
        print("PENDING DNG vertical actor-move trace")
        return 0
    source, move, alternate = [json.loads(path.read_text()) for path in
                               (SOURCE, MOVE, ALTERNATE)]
    require(all(item["timeout"] is None for item in (source, move, alternate)) and
            move["source_snapshot"] == alternate["source_snapshot"] == source["snapshot"] and
            move["working_game_disk"] == alternate["working_game_disk"] ==
            source["working_game_disk"], "DNG vertical move ancestry differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG vertical move game disk differs")
    before, after = checked_ram(source["snapshot"]), checked_ram(move["snapshot"])
    require(after == checked_ram(alternate["snapshot"]),
            "DNG vertical replay differs from independent next poll")
    checks = move["checkpoints"]
    require([item["pc"] for item in checks] ==
            ["0x98EC", "0x99D6", "0x99D9", "0x99DC", "0x99E5",
             "0x99F4", "0x99FE", "0x9A01", "0x8DDA"],
            "DNG vertical move checkpoints differ")
    require([item["slot"] for item in checks[1:8]] == ["03"] * 7 and
            [(item["actor_x"], item["actor_y"],
              item["old_cell_3_3"], item["new_cell_3_2"])
             for item in checks[1:8]] ==
            [("03", "03", "30", "00"),
             ("03", "03", "30", "00"),
             ("03", "03", "00", "00"),
             ("03", "02", "00", "00"),
             ("03", "02", "00", "00"),
             ("03", "02", "00", "00"),
             ("03", "02", "00", "30")],
            "DNG vertical move intermediate writes differ")
    require(" a=00 " in checks[2]["cpu"] and
            " a=30 " in checks[6]["cpu"] and
            before[0xA511] == after[0xA511] == 3 and
            before[0xA517] == after[0xA517] + 1 == 3 and
            before[0xB099 + 3 * 11 + 3] == 0x30 and
            after[0xB099 + 3 * 11 + 3] == 0 and
            before[0xB099 + 2 * 11 + 3] == 0 and
            after[0xB099 + 2 * 11 + 3] == 0x30,
            "DNG vertical move nibble or coordinate state differs")
    print("DNG slot 3: (3,3) $30→$00; Y 3→2; (3,2) $00→$30")
    print("Intermediate stores and full RAM match the independent next poll")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG vertical move verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
