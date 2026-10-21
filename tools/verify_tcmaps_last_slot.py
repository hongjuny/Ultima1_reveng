#!/usr/bin/env python3
"""Verify the final packed map copy and its first-input tail control."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"


def checked(item):
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private TCMAPS snapshot changed: {path}")
    return main_ram(path)


def main():
    if not (TRACE / "tcmaps-tail-effect/handoff.json").is_file():
        print("PENDING TCMAPS final-slot runtime copy and tail control")
        return 0
    source = json.loads((TRACE / "out-to-cas/handoff.json").read_text())
    copy = json.loads((TRACE / "tcmaps-last-slot/handoff.json").read_text())
    require(copy["source_snapshot"] == source["snapshot"] and
            copy["working_game_disk"] == source["working_game_disk"],
            "TCMAPS final-slot source differs")
    maps = (ROOT / "extracted/TCMAPS").read_bytes()
    require(len(maps) == 7660 and
            int.from_bytes(maps[18:20], "little") == 0x5AF0,
            "TCMAPS final pointer differs")
    ordinary = copy["trials"]["ordinary"]
    last = copy["trials"]["last"]
    for trial, slot, address in ((ordinary, 0, 0x4014), (last, 9, 0x5AF0)):
        ram = checked(trial["snapshot"])
        require(trial["slot"] == slot and trial["original_slot"] == 0 and
                trial["intervention"] ==
                (None if slot == 0 else {"address": "0x7EED", "value": 9}) and
                trial["source_address"] == f"0x{address:04X}" and
                trial["source_file_bytes"] == (768 if slot == 0 else 764) and
                trial["pre_load_tail"] == trial["loaded_tail"] == "ffffd5ff" and
                trial["final_cpu"].startswith("pc=89E0") and
                [p["pc"] for p in trial["checkpoints"]] ==
                ["0x898D", "0x89A3", "0x89CE", "0x89E0"] and
                ram[0x4000:0x4000+len(maps)] == maps and
                ram[0xB400:0xB700] == ram[address:address+768] and
                ram[0xB6FC:0xB700].hex() == trial["copied_tail"],
                f"TCMAPS slot {slot} copy differs")
    require(last["copied_tail"] == "ffffd5ff" and
            ordinary["copied_tail"] == maps[20+764:20+768].hex(),
            "TCMAPS copy tail differs")

    effect = json.loads((TRACE / "tcmaps-tail-effect/handoff.json").read_text())
    require(effect["source_snapshot"] == last["snapshot"] and
            effect["working_game_disk"] == copy["working_game_disk"] and
            effect["main_ram_differences"] ==
            ["0xB6FC", "0xB6FD", "0xB6FE", "0xB6FF"],
            "TCMAPS paired tail control differs")
    original = effect["trials"]["original"]
    cleared = effect["trials"]["cleared"]
    for trial, intervention, value in (
        (original, None, "ffffd5ff"),
        (cleared, {"address": "0xB6FC", "value": "00000000"}, "00000000"),
    ):
        ram = checked(trial["snapshot"])
        require(trial["intervention"] == intervention and
                trial["before"] == "ffffd5ff" and trial["at_input"] == value and
                trial["checkpoint"]["pc"] == "0x8A27" and
                trial["final_cpu"] == trial["checkpoint"]["cpu"] and
                ram[0xB6FC:0xB700].hex() == value,
                "TCMAPS first-input tail effect differs")
    print("TCMAPS slot 9: 764 file bytes plus inherited FF FF D5 FF at $5DEC-$5DEF")
    print("CAS first input: clearing copied $B6FC-$B6FF changes only those four RAM bytes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TCMAPS final-slot verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
