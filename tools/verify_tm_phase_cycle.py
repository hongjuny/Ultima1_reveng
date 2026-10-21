#!/usr/bin/env python3
"""Check the controlled TM flee, recovery, pursuit, and re-engagement replay."""

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
            f"TM phase-cycle snapshot changed: {path}")
    return report, main_ram(path)


def turn_chain(report, initial, phase, count):
    require(len(report["turns"]) == count and report["initial"] == initial and
            report["final_cpu"].startswith("pc=9815"), "TM wait trace header differs")
    prior = initial
    for index, turn in enumerate(report["turns"], 1):
        before, after = turn["before"], turn["after"]
        require(turn["number"] == index and turn["input"] == 32 and
                turn["boundary_pc"] == "0x9815" and before == prior and
                before["phase"] == phase and
                after["player_position"] == initial["player_position"],
                f"TM wait turn {index} differs")
        prior = after
    return prior


def check_ram(ram, state):
    require(int.from_bytes(ram[0x7EC6:0x7EC8], "little") == state["player_hp"] and
            int.from_bytes(ram[0x7EF4:0x7EF6], "little") == state["mondain_hp"] and
            ram[0x7EF2] == state["phase"] and
            list(ram[:2]) == state["player_position"] and
            list(ram[0xB628:0xB62A]) == state["mondain_position"],
            "TM phase-cycle final RAM differs")


def main():
    if not (TRACE / "tm-reengage/handoff.json").is_file():
        print("PENDING TM flee/recovery/re-engagement cycle")
        return 0
    battle, _ = checked("tm-phase-transition")
    flee, flee_ram = checked("tm-phase2-wait")
    require(flee["source_snapshot"] == battle["snapshot"] and
            flee["working_game_disk"] == battle["working_game_disk"] and
            flee["stop_mode"] == "phase-change", "TM flee source differs")
    initial = {k: v for k, v in battle["turns"][-1]["after"].items()
               if k != "gem_destroyed"}
    recovered = turn_chain(flee, initial, 2, 20)
    for index, turn in enumerate(flee["turns"], 1):
        before, after = turn["before"], turn["after"]
        require(after["player_hp"] == 2997 and
                after["mondain_hp"] == (484 if index <= 16 else 484 + 5 * (index - 16)) and
                after["phase"] == (2 if index < 20 else 1) and
                (after["mondain_position"] == [1, 1] if index >= 16 else True),
                f"TM flee/regeneration turn {index} differs")
    require(recovered == {"player_hp": 2997, "mondain_hp": 504, "phase": 1,
                          "player_position": [16, 4], "mondain_position": [1, 1]},
            "TM phase-one restoration differs")
    check_ram(flee_ram, recovered)

    pursuit, pursuit_ram = checked("tm-phase1-return")
    require(pursuit["source_snapshot"] == flee["snapshot"] and
            pursuit["working_game_disk"] == flee["working_game_disk"] and
            pursuit["stop_mode"] == "adjacent", "TM pursuit source differs")
    approached = turn_chain(pursuit, recovered, 1, 80)
    require(approached == {"player_hp": 2177, "mondain_hp": 504, "phase": 1,
                           "player_position": [16, 4], "mondain_position": [11, 4]} and
            all(t["after"]["mondain_position"] == [11, 4]
                for t in pursuit["turns"][14:]) and
            all(t["after"]["mondain_hp"] == 504 for t in pursuit["turns"]) and
            all(t["after"]["player_hp"] <= t["before"]["player_hp"]
                for t in pursuit["turns"]),
            "TM phase-one pursuit differs")
    check_ram(pursuit_ram, approached)

    distant, distant_ram = checked("tm-distant-attack")
    require(distant["source_snapshot"] == pursuit["snapshot"] and
            distant["working_game_disk"] == pursuit["working_game_disk"] and
            distant["final_cpu"].startswith("pc=9815") and
            len(distant["turns"]) == 9,
            "TM distant-attack source differs")
    prior = {**approached, "gem_destroyed": 1}
    for index, turn in enumerate(distant["turns"], 1):
        require(turn["number"] == index and turn["input"] == 32 and
                turn["before"] == prior and turn["at_entry"] == prior and
                turn["entry_pc"] ==
                ("0x99E7" if index in (3, 4, 5, 7, 9) else "0x9815") and
                turn["boundary_pc"] == "0x9815" and
                turn["after"]["mondain_position"] == [11, 4] and
                turn["after"]["mondain_hp"] == 504,
                f"TM distant attack turn {index} differs")
        prior = turn["after"]
    require(prior["player_hp"] == 2164 and
            all(t["after"]["player_hp"] == 2177 for t in distant["turns"][:-1]),
            "TM distant attack HP effect differs")
    check_ram(distant_ram, prior)

    reengage, final_ram = checked("tm-reengage")
    require(reengage["source_snapshot"] == pursuit["snapshot"] and
            reengage["working_game_disk"] == pursuit["working_game_disk"] and
            reengage["end_reason"] == "phase changed" and
            reengage["final_cpu"].startswith("pc=9815") and
            len(reengage["turns"]) == 7,
            "TM re-engagement source differs")
    prior = {**approached, "gem_destroyed": 1}
    for index, turn in enumerate(reengage["turns"], 1):
        require(turn["number"] == index and turn["before"] == prior and
                turn["boundary_pc"] == "0x9815" and
                turn["after"]["gem_destroyed"] == 1 and
                turn["after"]["mondain_hp"] <= turn["before"]["mondain_hp"] and
                (turn["action"], turn["input"]) ==
                (("attack", [65, 11]) if index == 7 else
                 ("approach", [8] if index <= 3 else
                  [10] if index == 4 else [8])),
                f"TM re-engagement turn {index} differs")
        prior = turn["after"]
    require(prior == {"player_hp": 2005, "mondain_hp": 492, "phase": 2,
                      "gem_destroyed": 1, "player_position": [11, 5],
                      "mondain_position": [11, 3]},
            "TM re-engagement phase change differs")
    check_ram(final_ram, prior)
    print("TM: 16 flee turns to corner, four blocked turns 484→504 and phase 2→1")
    print("TM: 80 pursuit waits, seven routed actions, attack 504→492 and phase 1→2")
    print("TM: distant branch $99E7 hit on five of nine waits; last reduced HP 2177→2164")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"TM phase-cycle verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
