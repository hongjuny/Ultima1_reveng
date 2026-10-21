#!/usr/bin/env python3
"""Reenter the second castle with a completed odd quest after resurrection."""

import json
from pathlib import Path
import sys

from disassemble import ROOT
from trace_cas_first_input import main as castle_poll
from trace_out_enter_04 import main as outdoor_enter
from trace_out_to_cas import main as castle_load
from verify_intro_support import main_ram


SOURCE = ROOT / "build/traces/odd-quest-return-castle-route/step-73/handoff.json"
OUTPUT = ROOT / "build/traces/odd-quest-reenter-castle"


def main():
    enter, load, poll = (OUTPUT / name for name in ("enter", "load", "poll"))
    if outdoor_enter(SOURCE, enter, expected_coords=bytes((22, 20))):
        raise RuntimeError("castle E transition failed")
    if castle_load(enter / "handoff.json", load):
        raise RuntimeError("CAS overlay load failed")
    if castle_poll(load / "handoff.json", poll):
        raise RuntimeError("CAS first input failed")
    report = json.loads((poll / "handoff.json").read_text())
    ram = main_ram(Path(report["snapshot"]["path"]))
    state = {"position": list(ram[:2]), "castle_index": ram[0x9E3B],
             "quest": list(ram[0x7EA9:0x7EB1]),
             "gems": list(ram[0x7E75:0x7E79]),
             "world_location": ram[0x7EED], "group": ram[0x7E6F]}
    if state != {"position": [0, 9], "castle_index": 1,
                 "quest": [0, 255, 0, 0, 0, 0, 0, 0],
                 "gems": [0] * 4, "world_location": 1, "group": 0}:
        raise RuntimeError(f"completed quest lost at castle reentry: {state}")
    (OUTPUT / "route.json").write_text(json.dumps({
        "source_report": str(SOURCE), "enter_report": str(enter / "handoff.json"),
        "load_report": str(load / "handoff.json"),
        "poll_report": str(poll / "handoff.json"), "state": state}, indent=2) + "\n")
    print(f"completed quest at castle input: {state}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"odd quest castle reentry failed: {error}", file=sys.stderr)
        raise SystemExit(1)
