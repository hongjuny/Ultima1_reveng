#!/usr/bin/env python3
"""Enter the dungeon with the naturally accepted odd quest still active."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_dng_first_input import main as dungeon_poll
from trace_out_enter_07 import main as outdoor_enter
from trace_out_to_dng import main as dungeon_load
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/odd-quest-route-to-dng/step-26/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-dng-entry"


def main():
    enter, load, poll = (OUTPUT / name for name in ("enter", "load", "poll"))
    if outdoor_enter(SOURCE, enter):
        raise RuntimeError("dungeon E transition failed")
    if dungeon_load(enter / "handoff.json", load):
        raise RuntimeError("DNG overlay load failed")
    if dungeon_poll(load / "handoff.json", poll):
        raise RuntimeError("DNG first input failed")
    report = json.loads((poll / "handoff.json").read_text())
    ram = main_ram(Path(report["snapshot"]["path"]))
    state = {"position": list(ram[:2]), "quest": list(ram[0x7EA9:0x7EB1]),
             "depth": ram[0xA506], "local_position": list(ram[0xA4E8:0xA4EA])}
    if state["position"] != [43, 15] or state["quest"] != [0, 1, 0, 0, 0, 0, 0, 0]:
        raise RuntimeError(f"accepted quest lost at dungeon entry: {state}")
    (OUTPUT / "route.json").write_text(json.dumps({
        "source_report": str(SOURCE), "enter_report": str(enter / "handoff.json"),
        "load_report": str(load / "handoff.json"),
        "poll_report": str(poll / "handoff.json"), "state": state}, indent=2) + "\n")
    print(f"accepted quest at first DNG poll: {state}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest dungeon entry failed: {error}", file=sys.stderr)
        raise SystemExit(1)
