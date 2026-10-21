#!/usr/bin/env python3
"""Search ordinary stair turns for an active type-five third-floor monster."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_dng_descend import observe
from trace_dng_level2_to3 import play_key
from trace_dng_stairs_k import main as stair_k
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/odd-quest-descend/level-2/stairs-turn/poll/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-spawn-search"


def state(path):
    report = json.loads(path.read_text())
    ram = main_ram(Path(report["snapshot"]["path"]))
    position, facing, depth, grid, hp = observe(report)
    return ram, position, facing, depth, hp


def main(max_waits=6):
    source = SOURCE
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trials = []
    for waits in range(max_waits + 1):
        ram, position, facing, depth, hp = state(source)
        if position != (7, 3) or facing != (0, -1) or depth != 2 or ram[0x7EAA] != 1:
            raise RuntimeError(f"stair source changed at wait {waits}")
        if hp < 25:
            raise RuntimeError(f"HP too low for further ordinary waiting: {hp}")
        trial = OUTPUT / f"wait-{waits:02d}/descent"
        if stair_k(source, trial, expected_tile="07", expected_depth="02",
                   branch="descend", expected_position="0703",
                   expected_facing="00ff"):
            raise RuntimeError(f"stair trial {waits} failed")
        result = trial / "handoff.json"
        after, _, _, after_depth, after_hp = state(result)
        slot = {"active": after[0xA50D] == 0,
                "position": [after[0xA513], after[0xA519]],
                "hp": int.from_bytes(after[0xA51F:0xA520] + after[0xA525:0xA526],
                                     "little")}
        entry = {"waits": waits, "source_report": str(source),
                 "result_report": str(result), "player_hp": after_hp,
                 "slot5": slot}
        trials.append(entry)
        (OUTPUT / "search.json").write_text(json.dumps(trials, indent=2) + "\n")
        print(f"waits={waits} depth={after_depth} player_hp={after_hp} "
              f"slot5={slot}", flush=True)
        if after_depth != 3 or after[0x7EAA] != 1:
            raise RuntimeError("accepted quest lost during stair trial")
        if slot["active"] and after_hp >= 25:
            (OUTPUT / "selected.json").write_text(json.dumps(entry, indent=2) + "\n")
            print(f"selected ordinary third-floor spawn: {result}", flush=True)
            return
        if waits < max_waits:
            source = play_key(0x20, source, OUTPUT / f"wait-{waits+1:02d}/space")
    raise RuntimeError("type-five spawn not found in bounded ordinary stair turns")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest spawn search failed: {error}", file=sys.stderr)
        raise SystemExit(1)
