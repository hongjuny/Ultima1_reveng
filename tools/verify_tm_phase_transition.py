#!/usr/bin/env python3
"""Verify TM's natural damage and controlled 1000-HP flee transition."""

import json
from pathlib import Path
import sys

from baseline import describe
from disassemble import ROOT
from verify_intro_support import main_ram, require


TRACE = ROOT / "build/traces"


def checked(name):
    report = json.loads((TRACE / name / "handoff.json").read_text())
    item = report["snapshot"]
    path = Path(item["path"])
    require(describe(path) == {"size": item["size"], "sha256": item["sha256"]},
            f"private TM snapshot changed: {path}")
    return report, main_ram(path)


def main():
    if not (TRACE / "tm-phase-transition/handoff.json").is_file():
        print("PENDING TM combat phase transition")
        return 0
    tm = (ROOT / "extracted/TM").read_bytes()
    at = lambda address, length: tm[address-0x8956:address-0x8956+length]
    require(at(0x8FC8, 18) == bytes.fromhex(
        "b0 23 ad f5 7e 30 1f d0 05 ad f4 7e f0 18 ad 76 a4 c9") and
        at(0x8FE5, 9) == bytes.fromhex("a9 02 8d f2 7e 20 64 9c 60") and
        at(0x98ED, 11) == bytes.fromhex("49 80 85 04 a5 05 d0 06 20 b9 15") and
        at(0x9900, 16) == bytes.fromhex(
            "36 99 90 31 ad f5 7e 30 2c 18 ad f4 7e 69 05 8d") and
        at(0x9925, 5) == bytes.fromhex("a9 01 8d f2 7e") and
        at(0x99BF, 24) == bytes.fromhex(
            "ad c6 7e 85 c3 ad c7 7e 85 c4 a0 05 46 c4 66 c3 88 d0 f9 a9 14 20 54 82"),
            "TM phase and retaliation code differs from extraction")
    gem, _ = checked("tm-gem-command")
    first, _ = checked("tm-attack-direction")
    first_next, ram = checked("tm-after-attack")
    require(first_next["source_snapshot"] == first["snapshot"] and
            [p["pc"] for p in first_next["checkpoints"]] ==
            ["0x8EA2", "0x8E5E", "0x9815"] and
            first_next["before"]["player_hp"] == 28 and
            first_next["after"]["player_hp"] == 10 and
            first_next["after"]["mondain_hp"] == 970 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 10,
            "natural first TM retaliation differs")
    second, _ = checked("tm-second-attack")
    second_next, ram = checked("tm-after-second-attack")
    require(second["source_snapshot"] == first_next["snapshot"] and
            [p["pc"] for p in second["checkpoints"]][-1] == "0x8F73" and
            second_next["source_snapshot"] == second["snapshot"] and
            second_next["after"]["player_hp"] == 5 and
            second_next["after"]["mondain_hp"] == 970 and
            int.from_bytes(ram[0x7EC6:0x7EC8], "little") == 5,
            "natural second TM retaliation differs")
    battle, ram = checked("tm-phase-transition")
    require(battle["source_snapshot"] == gem["snapshot"] and
            battle["intervention"] == {"address": "0x7EC6", "player_hp": 10000} and
            battle["original"] == {"player_hp": 28, "mondain_hp": 1000,
                                   "phase": 1, "gem_destroyed": 1,
                                   "player_position": [14, 5],
                                   "mondain_position": [15, 5]} and
            battle["end_reason"] == "phase-two observation complete" and
            len(battle["turns"]) == 43 and
            battle["final_cpu"].startswith("pc=9815"),
            "controlled TM phase source differs")
    prior = None
    for index, turn in enumerate(battle["turns"], 1):
        require(turn["number"] == index and turn["boundary_pc"] == "0x9815" and
                turn["before"]["gem_destroyed"] == 1 and
                turn["after"]["gem_destroyed"] == 1 and
                (prior is None or turn["before"] == prior),
                f"TM phase turn {index} lineage differs")
        if index <= 36:
            before, after = turn["before"], turn["after"]
            damage = before["player_hp"] - after["player_hp"]
            require(turn["action"] == "attack" and turn["input"] == [65, 21] and
                    before["phase"] == after["phase"] == 1 and
                    before["mondain_hp"] >= after["mondain_hp"] and
                    before["player_hp"] // 32 <= damage <= before["player_hp"] // 32 + 19,
                    f"TM phase-one damage turn {index} differs")
        prior = turn["after"]
    transition = battle["turns"][36]
    regen = battle["turns"][40]
    counter = battle["turns"][41]
    require(transition["action"] == "attack" and
            (transition["before"]["mondain_hp"], transition["after"]["mondain_hp"]) ==
            (513, 482) and
            (transition["before"]["phase"], transition["after"]["phase"]) == (1, 2) and
            transition["after"]["mondain_position"] == [16, 5] and
            regen["action"] == "approach" and
            (regen["before"]["mondain_hp"], regen["after"]["mondain_hp"]) ==
            (482, 487) and
            counter["action"] == "attack" and
            (counter["before"]["mondain_hp"], counter["after"]["mondain_hp"]) ==
            (487, 484) and
            battle["turns"][-1]["after"]["mondain_hp"] == 484 and
            int.from_bytes(ram[0x7EF4:0x7EF6], "little") == 484 and
            ram[0x7EF2] == 2,
            "TM flee transition, regeneration, or follow-up hit differs")
    checkpoint = battle["pre_regen_snapshot"]
    require(describe(Path(checkpoint["path"])) ==
            {"size": checkpoint["size"], "sha256": checkpoint["sha256"]},
            "TM pre-regeneration snapshot changed")
    checkpoint_ram = main_ram(Path(checkpoint["path"]))
    require(int.from_bytes(checkpoint_ram[0x7EF4:0x7EF6], "little") == 482 and
            checkpoint_ram[0x7EF2] == 2 and
            list(checkpoint_ram[:2]) == [17, 5] and
            list(checkpoint_ram[0xB628:0xB62A]) == [17, 3],
            "TM pre-regeneration state differs")
    boundary = json.loads((TRACE / "tm-regen-boundary/handoff.json").read_text())
    require(boundary["source_snapshot"] == checkpoint and
            boundary["working_game_disk"] == battle["working_game_disk"],
            "TM regeneration boundary ancestry differs")
    for label, hp, phase in (("original", 487, 2), ("hp-495", 500, 1)):
        trial = boundary["trials"][label]
        item = trial["snapshot"]
        trial_ram = main_ram(Path(item["path"]))
        require(describe(Path(item["path"])) ==
                {"size": item["size"], "sha256": item["sha256"]} and
                trial["intervention"] == (None if label == "original" else
                                          {"address": "0x7EF4", "mondain_hp": 495}) and
                trial["input"] == 11 and
                trial["before"] == {key: value for key, value in
                                    battle["turns"][39]["after"].items()
                                    if key != "gem_destroyed"} and
                [p["pc"] for p in trial["checkpoints"]] ==
                ["0x8E5E", "0x9815"] and
                trial["after"] == {"player_hp": 2997, "mondain_hp": hp,
                                   "phase": phase, "player_position": [17, 4],
                                   "mondain_position": [17, 3]} and
                int.from_bytes(trial_ram[0x7EF4:0x7EF6], "little") == hp and
                trial_ram[0x7EF2] == phase,
                f"TM regeneration boundary trial differs: {label}")
    print("TM phase one: Mondain 1000→482 over 37 attacks; player damage HP/32 + 0..19")
    print("below 500: phase 1→2, flee; blocked move regenerates 5; 495→500 restores phase 1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM phase transition verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
