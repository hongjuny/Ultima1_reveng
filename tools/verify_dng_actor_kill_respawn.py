#!/usr/bin/env python3
"""Check ordinary lethal attack, map restoration, and immediate respawn."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"
SOURCE = TRACE / "dng-attack-repeat-3/poll/handoff.json"
KILL = TRACE / "dng-actor-kill-respawn/handoff.json"
ALTERNATE = TRACE / "dng-attack-repeat-3/key/handoff.json"


def checked_ram(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"DNG lethal attack snapshot differs: {path}")
    return main_ram(path)


def main() -> int:
    if not all(path.is_file() for path in (SOURCE, KILL, ALTERNATE)):
        print("PENDING DNG lethal actor attack")
        return 0
    source, kill, alternate = [json.loads(path.read_text()) for path in
                               (SOURCE, KILL, ALTERNATE)]
    require(all(item["timeout"] is None for item in
                (source, kill, alternate)) and
            kill["source_snapshot"] == alternate["source_snapshot"] ==
            source["snapshot"] and
            kill["working_game_disk"] == alternate["working_game_disk"] ==
            source["working_game_disk"], "DNG kill replay ancestry differs")
    disk = source["working_game_disk"]
    require(describe(Path(disk["path"])) ==
            {"size": disk["size"], "sha256": disk["sha256"]},
            "DNG kill replay game disk differs")
    before, after = checked_ram(source["snapshot"]), checked_ram(kill["snapshot"])
    require(after == checked_ram(alternate["snapshot"]),
            "DNG kill replay differs from independent A handler return")
    points = kill["checkpoints"]
    require([item["pc"] for item in points] ==
            ["0x9077", "0x90A9", "0x93A7", "0x93B2", "0x93C6",
             "0x93DD", "0x9437", "0x9447", "0x8E0E"],
            "DNG lethal attack checkpoints differ")
    require([item["slot1_flag"] for item in points] ==
            ["00", "00", "00", "01", "01", "00", "00", "00", "00"] and
            [item["slot1_hp_word"] for item in points] ==
            ["0600", "f2ff", "f2ff", "f2ff", "f2ff", "f2ff",
             "0b00", "0b00", "0b00"] and
            [item["old_cell_4_1"] for item in points] ==
            ["13", "13", "13", "13", "03", "03", "03", "03", "03"] and
            [item["new_cell_1_7"] for item in points] ==
            ["00"] * 7 + ["10", "10"] and
            all(item["damage_a4f3_a4f4"] == "1400" for item in points[:6]) and
            all(item["slot1_x_y"] == "0401" for item in points[:6]) and
            all(item["slot1_x_y"] == "0107" for item in points[6:]) and
            points[5]["spawn_slot_a4fe"] == "01",
            "DNG lethal attack intermediate state differs")
    initial_map = bytes.fromhex(points[0]["map_hex"])
    cleared_map = bytes.fromhex(points[4]["map_hex"])
    respawned_map = bytes.fromhex(points[7]["map_hex"])
    old_index, new_index = 11 + 4, 7 * 11 + 1
    expected = bytearray(initial_map)
    expected[old_index] = 0x03
    require(bytes(expected) == cleared_map, "DNG removal changed other map cells")
    expected[new_index] = 0x10
    require(bytes(expected) == respawned_map == bytes.fromhex(points[8]["map_hex"]),
            "DNG respawn changed other map cells")
    require(before[0xA509] == after[0xA509] == 0 and
            before[0xA51B] == 6 and after[0xA51B] == 11 and
            (before[0xA50F], before[0xA515]) == (4, 1) and
            (after[0xA50F], after[0xA515]) == (1, 7),
            "DNG final actor state differs")
    print("DNG lethal A: slot 1 HP 6−20→$FFF2; flag 0→1→0")
    print("Old (4,1) $13→$03; same slot respawned (1,7) $00→$10 with HP 11")
    print("Intermediate maps and full RAM match an independent handler replay")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"DNG lethal actor verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
